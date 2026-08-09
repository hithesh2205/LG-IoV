import argparse
import random
import torch
import numpy as np
import os
import time
import json
from rich.console import Console
from rich.table import Table

from preprocessing import PreprocessingPipeline
from model import ChebyKAN
from fhe_engine import DesignatedDecryptor
from federated import Client, Server
from ga_search import run_ga_search
from sklearn.metrics import f1_score, roc_auc_score, confusion_matrix, accuracy_score

console = Console()

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def evaluate_model(model, X, y):
    model.eval()
    tensor_x = torch.Tensor(X)
    tensor_y = torch.LongTensor(y)
    
    with torch.no_grad():
        outputs = model(tensor_x)
        probs = torch.softmax(outputs, dim=1)
        preds = torch.argmax(probs, dim=1)
        
        acc = accuracy_score(y, preds.numpy())
        macro_f1 = f1_score(y, preds.numpy(), average='macro', zero_division=0)
        
        # Safe ROC-AUC for multi-class
        try:
            # Need one-hot for roc_auc if multi-class
            n_classes = outputs.shape[1]
            if n_classes > 2:
                y_onehot = np.eye(n_classes)[y]
                roc = roc_auc_score(y_onehot, probs.numpy(), average='macro', multi_class='ovr')
            else:
                roc = roc_auc_score(y, probs[:, 1].numpy())
        except ValueError:
            roc = 0.0 # fallback if only one class present in test
            
        cm = confusion_matrix(y, preds.numpy())
        
    return acc, macro_f1, roc, cm

def print_dirichlet_skew(client_class_counts, classes):
    table = Table(title="Per-Client Dirichlet Class Distribution")
    table.add_column("Client ID", justify="center", style="cyan")
    for c in classes:
        table.add_column(f"Class {c}", justify="right", style="magenta")
        
    for i in range(len(client_class_counts)):
        row = [f"Client {i}"]
        for c in classes:
            row.append(str(client_class_counts[i][c]))
        table.add_row(*row)
        
    console.print(table)

def main():
    parser = argparse.ArgumentParser(description="ChebyKAN + Full Layer-wise CKKS FHE Simulation")
    parser.add_argument('--dataset', type=str, required=True, choices=['car_hack', 'vtc_can', 'veremi', 'cicids'])
    parser.add_argument('--rounds', type=int, default=5)
    parser.add_argument('--smoke', action='store_true', help="Run in smoke test mode (1 round, subset data)")
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    set_seed(args.seed)
    console.print(f"[bold green]Starting ChebyKAN FHE Simulation on {args.dataset}[/bold green]")
    
    # Paths mapping
    base_dirs = {
        'car_hack': r'C:\Users\Thrish_Sudha\Desktop\Amrita Files\LGSI IOV\Team\LG_IoV\Preprocessed_Dataset\Car_hack_pro',
        'vtc_can': r'C:\Users\Thrish_Sudha\Desktop\Amrita Files\LGSI IOV\Team\LG_IoV\Preprocessed_Dataset\Can_vtc_pro',
        'veremi': r'C:\Users\Thrish_Sudha\Desktop\Amrita Files\LGSI IOV\Team\LG_IoV\Preprocessed_Dataset\VeReMi_pro',
        'cicids': r'C:\Users\Thrish_Sudha\Desktop\Amrita Files\LGSI IOV\Team\LG_IoV\Preprocessed_Dataset\CICIDS_pro'
    }
    
    pipeline = PreprocessingPipeline(window_size=64, stride=16, n_clients=10, alpha=0.3)
    
    # Preprocessing
    X_train, y_train, X_val, y_val, X_test, y_test, class_names, meta = pipeline.fit_transform(
        args.dataset, base_dirs[args.dataset], smoke_mode=args.smoke
    )
    
    # Map string labels to int
    label_map = {name: i for i, name in enumerate(class_names)}
    y_train = np.array([label_map[y] for y in y_train])
    y_val = np.array([label_map[y] for y in y_val])
    y_test = np.array([label_map[y] for y in y_test])
    
    if args.smoke:
        console.print("[yellow]--- SMOKE MODE ENABLED ---[/yellow]")
        args.rounds = 1
        # Truncate dataset
        X_train, y_train = X_train[:500], y_train[:500]
        X_val, y_val = X_val[:100], y_val[:100]
        X_test, y_test = X_test[:100], y_test[:100]
        # Truncate client indices to match
        for k in meta['client_indices']:
            meta['client_indices'][k] = [idx for idx in meta['client_indices'][k] if idx < 500]

    print_dirichlet_skew(meta['client_class_counts'], class_names)
    
    num_classes = len(class_names)
    
    # GA Search
    best_config = run_ga_search(args.dataset, X_train, y_train, X_val, y_val, num_classes, smoke_mode=args.smoke)
    
    # FHE Setup
    console.print("Initializing TenSEAL CKKS Context...")
    decryptor = DesignatedDecryptor()
    public_context = decryptor.get_public_context()
    
    # Model Setup
    model = ChebyKAN(in_features=46, hidden_features=64, num_classes=num_classes, degree=5)
    
    # Clients Setup
    clients = []
    for i in range(10):
        # Handle cases where client has 0 samples (e.g. smoke mode or high skew)
        indices = meta['client_indices'].get(i, [])
        if len(indices) > 0:
            client_X = X_train[indices]
            client_y = y_train[indices]
            clients.append(Client(i, client_X, client_y, batch_size=best_config['batch_size'], epochs=best_config['epochs']))
            
    if len(clients) == 0:
        raise ValueError("No clients have data to train on!")
        
    server = Server(model, public_context, decryptor)
    
    # Simulation Report
    report = {
        'dataset': args.dataset,
        'rounds': []
    }
    
    report_table = Table(title=f"Proof of Work & Smoke Test Results - {args.dataset.upper()}")
    report_table.add_column("Round", justify="center")
    report_table.add_column("Wall-clock Time (s)")
    report_table.add_column("Rejected Clients")
    report_table.add_column("Global Test Acc")
    report_table.add_column("Macro-F1")
    report_table.add_column("ROC-AUC")
    
    for r in range(args.rounds):
        console.print(f"\n[bold blue]--- Global Round {r+1}/{args.rounds} ---[/bold blue]")
        t0 = time.time()
        
        # fraction=1.0 for smoke to test Krum rejection logic effectively, otherwise 0.7
        fraction = 1.0 if args.smoke else 0.7
        rejected_count = server.round(clients, fraction=fraction, f=1)
        
        t1 = time.time()
        round_time = t1 - t0
        
        acc, f1, roc, cm = evaluate_model(server.global_model, X_test, y_test)
        
        console.print(f"Round {r+1} Time: {round_time:.2f}s, Test Acc: {acc:.4f}, F1: {f1:.4f}, ROC: {roc:.4f}")
        
        report_table.add_row(
            str(r+1),
            f"{round_time:.2f}",
            str(rejected_count),
            f"{acc:.4f}",
            f"{f1:.4f}",
            f"{roc:.4f}"
        )
        
        report['rounds'].append({
            'round': r+1,
            'time_s': round_time,
            'rejected': rejected_count,
            'test_acc': acc,
            'macro_f1': f1,
            'roc_auc': roc,
            'confusion_matrix': cm.tolist()
        })
        
        # Checkpoint
        torch.save(server.global_model.state_dict(), f"checkpoint_{args.dataset}_round{r+1}.pt")
        
    console.print(report_table)
    
    with open(f"report_{args.dataset}.json", "w") as f:
        json.dump(report, f, indent=4)
        
    with open(f"report_{args.dataset}.md", "w") as f:
        f.write(f"# Proof of Work - {args.dataset.upper()}\n\n")
        f.write(f"Total Rounds: {args.rounds}\n")
        f.write(f"Best Config: {best_config}\n\n")
        f.write("## Round Metrics\n")
        for rnd in report['rounds']:
            f.write(f"- Round {rnd['round']}: Acc {rnd['test_acc']:.4f}, F1 {rnd['macro_f1']:.4f}, Time {rnd['time_s']:.2f}s\n")
            
    console.print(f"[bold green]Simulation Complete! Report saved to report_{args.dataset}.json and .md[/bold green]")

if __name__ == "__main__":
    main()
