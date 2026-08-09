import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
import numpy as np
import copy
from fhe_engine import encrypt_tensor
from aggregation import homomorphic_multi_krum_distances, multi_krum_select, homomorphic_fedavg
from rich.console import Console
console = Console()

class Client:
    def __init__(self, client_id, X_train, y_train, batch_size=96, lr=5e-4, epochs=1):
        self.client_id = client_id
        
        # Data
        tensor_x = torch.Tensor(X_train)
        tensor_y = torch.LongTensor(y_train)
        self.dataloader = DataLoader(TensorDataset(tensor_x, tensor_y), batch_size=batch_size, shuffle=True)
        
        self.lr = lr
        self.epochs = epochs
        
    def local_train(self, global_model, public_context):
        """
        Receives global plaintext model, trains locally, and returns ENCRYPTED updates.
        """
        # console.print(f"[Client {self.client_id}] Status: Training")
        model = copy.deepcopy(global_model)
        model.train()
        optimizer = optim.AdamW(model.parameters(), lr=self.lr)
        criterion = nn.CrossEntropyLoss()
        
        for e in range(self.epochs):
            for data, target in self.dataloader:
                optimizer.zero_grad()
                output = model(data)
                loss = criterion(output, target)
                loss.backward()
                optimizer.step()
                
        # console.print(f"[Client {self.client_id}] Status: Encrypting")
        encrypted_update = {}
        for name, param in model.named_parameters():
            if param.requires_grad:
                encrypted_update[name] = encrypt_tensor(param.data, public_context)
                
        # console.print(f"[Client {self.client_id}] Status: Uploading")
        
        # Also return plaintext weights for the server's verification path
        plaintext_weights = {name: param.data.clone() for name, param in model.named_parameters() if param.requires_grad}
        
        return encrypted_update, plaintext_weights, len(self.dataloader.dataset)

class Server:
    def __init__(self, global_model, public_context, decryptor):
        self.global_model = global_model
        self.public_context = public_context
        self.decryptor = decryptor # Designated aggregator
        
        assert not hasattr(self.public_context, "secret_key") or not self.public_context.has_secret_key(), "Server public context holds secret key!"
        
    def round(self, clients, fraction=0.7, f=1):
        num_selected = max(1, int(fraction * len(clients)))
        selected_clients = np.random.choice(clients, num_selected, replace=False)
        
        encrypted_updates = []
        plaintext_updates = []
        sample_counts = []
        
        console.print("[yellow]Note: Simplification vs Multi-Key - Server distributes aggregated PLAINTEXT model post-decryption each round.[/yellow]")
        
        for client in selected_clients:
            enc_up, plain_up, count = client.local_train(self.global_model, self.public_context)
            encrypted_updates.append(enc_up)
            plaintext_updates.append(plain_up)
            sample_counts.append(count)
            
        # Homomorphic Multi-Krum
        console.print("[Server] Computing Homomorphic Multi-Krum Distances...")
        enc_distances = homomorphic_multi_krum_distances(encrypted_updates)
        
        # Decrypt distances for selection (only the distances, not the model weights!)
        console.print("[Decryptor] Decrypting distance matrix for client selection...")
        num_c = len(encrypted_updates)
        dec_distances = np.zeros((num_c, num_c))
        for i in range(num_c):
            for j in range(i+1, num_c):
                # Decrypt scalar
                enc_distances[i][j].link_context(self.decryptor.context)
                val = enc_distances[i][j].decrypt()[0]
                dec_distances[i][j] = val
                dec_distances[j][i] = val
                
        selected_idx, rejected_idx, scores = multi_krum_select(dec_distances, num_c, f=f)
        
        for i, score in enumerate(scores):
            status = "REJECTED" if i in rejected_idx else "ACCEPTED"
            console.print(f"Client {selected_clients[i].client_id} Score: {score:.4f} -> {status}")
            
        # Filter updates
        accepted_enc = [encrypted_updates[i] for i in selected_idx]
        accepted_plain = [plaintext_updates[i] for i in selected_idx]
        accepted_counts = [sample_counts[i] for i in selected_idx]
        
        total_samples = sum(accepted_counts)
        weights = [c / total_samples for c in accepted_counts]
        
        # Homomorphic FedAvg
        console.print("[Server] Computing Homomorphic FedAvg...")
        agg_enc = homomorphic_fedavg(accepted_enc, weights)
        
        # Decrypt and update global model
        console.print("[Decryptor] Decrypting Aggregated Model...")
        max_error = 0.0
        
        for name, param in self.global_model.named_parameters():
            if param.requires_grad:
                shape = param.data.shape
                dec_tensor = self.decryptor.decrypt_tensor(agg_enc[name], shape)
                
                # Integrity Verification vs Plaintext FedAvg
                plain_agg = sum(accepted_plain[i][name] * weights[i] for i in range(len(selected_idx)))
                error = torch.max(torch.abs(dec_tensor - plain_agg)).item()
                if error > max_error:
                    max_error = error
                    
                param.data.copy_(dec_tensor)
                
        console.print(f"[Verification] Max Absolute HE Error vs Plaintext: {max_error:.6e}")
        return len(rejected_idx)
