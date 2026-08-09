import tenseal as ts
import numpy as np

def homomorphic_fedavg(client_updates, weights):
    """
    client_updates: List of dicts, each containing {'layer_name': CKKSVector, ...}
    weights: List of scalars representing sample fraction per client.
    
    Returns:
    aggregated_update: dict of {'layer_name': CKKSVector}
    """
    num_clients = len(client_updates)
    assert num_clients == len(weights)
    
    aggregated = {}
    layer_names = client_updates[0].keys()
    
    for name in layer_names:
        # Multiply first client by its weight
        agg_vec = client_updates[0][name] * weights[0]
        
        # Add the rest
        for i in range(1, num_clients):
            agg_vec = agg_vec + (client_updates[i][name] * weights[i])
            
        aggregated[name] = agg_vec
        
    return aggregated

def homomorphic_multi_krum_distances(client_updates):
    """
    Compute homomorphic squared Euclidean distances between clients.
    client_updates: List of dicts, each containing {'layer_name': CKKSVector}
    
    Returns:
    distances: 2D array-like of CKKSVectors of shape (num_clients, num_clients)
               where element (i, j) is the sum of squared diffs over all layers.
    """
    num_clients = len(client_updates)
    layer_names = client_updates[0].keys()
    
    # Initialize distances matrix
    distances = [[None for _ in range(num_clients)] for _ in range(num_clients)]
    
    for i in range(num_clients):
        for j in range(i + 1, num_clients):
            total_dist = None
            for name in layer_names:
                diff = client_updates[i][name] - client_updates[j][name]
                sq_diff = diff.square()
                
                # sum() is not directly available for TenSEAL vectors, 
                # but we can do dot product with all ones, or just keep it as vector and sum after decryption
                # Actually, TenSEAL vectors have a .sum() method! But wait, no, dot with ones is safer if .sum() is missing.
                # Let's use dot product with a plaintext vector of ones.
                ones = [1.0] * diff.size()
                layer_dist = sq_diff.dot(ones)
                
                if total_dist is None:
                    total_dist = layer_dist
                else:
                    total_dist = total_dist + layer_dist
                    
            distances[i][j] = total_dist
            distances[j][i] = total_dist
            
    return distances

def multi_krum_select(decrypted_distances, num_clients, f=1):
    """
    decrypted_distances: 2D numpy array of scalar distances
    f: assumed Byzantine tolerance
    Returns boolean list indicating selected clients
    """
    k = num_clients - f - 2
    if k < 1:
        k = 1 # Fallback if too few clients
        
    scores = []
    for i in range(num_clients):
        # Sort distances for client i
        dists = sorted([decrypted_distances[i][j] for j in range(num_clients) if i != j])
        # Sum of k-nearest neighbors
        score = sum(dists[:k])
        scores.append(score)
        
    # We reject the f highest scoring clients
    sorted_indices = np.argsort(scores)
    selected_indices = sorted_indices[:-f] if f > 0 else sorted_indices
    rejected_indices = sorted_indices[-f:] if f > 0 else []
    
    return selected_indices, rejected_indices, scores
