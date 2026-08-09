import torch
import torch.nn as nn
import torch.nn.functional as F

class ChebyKANLayer(nn.Module):
    def __init__(self, in_features, out_features, degree=5):
        super(ChebyKANLayer, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.degree = degree
        
        # Base weight
        self.base_weight = nn.Parameter(torch.Tensor(out_features, in_features))
        
        # Chebyshev weight
        self.cheby_weight = nn.Parameter(torch.Tensor(out_features, in_features, degree))
        
        # Bias
        self.bias = nn.Parameter(torch.Tensor(out_features))
        
        self.reset_parameters()
        
    def reset_parameters(self):
        nn.init.kaiming_uniform_(self.base_weight, a=np.sqrt(5) if 'np' in globals() else 2.236)
        nn.init.kaiming_uniform_(self.cheby_weight, a=np.sqrt(5) if 'np' in globals() else 2.236)
        fan_in, _ = nn.init._calculate_fan_in_and_fan_out(self.base_weight)
        bound = 1 / (fan_in ** 0.5) if fan_in > 0 else 0
        nn.init.uniform_(self.bias, -bound, bound)

    def forward(self, x):
        # x is (batch_size, in_features)
        x = torch.tanh(x) # Defensive squash to [-1, 1]
        
        # Compute Chebyshev polynomials T_n(x)
        T = [torch.ones_like(x), x]
        for n in range(2, self.degree):
            T.append(2 * x * T[n-1] - T[n-2])
            
        # T is a list of tensors of shape (batch, in_features)
        # Stack to (batch, in_features, degree)
        T_stack = torch.stack(T, dim=-1)
        
        # Contract with cheby_weight: (out, in, deg) * (batch, in, deg) -> (batch, out)
        # We can use einsum
        cheby_out = torch.einsum('oid,bid->bo', self.cheby_weight, T_stack)
        
        # Base linear output
        base_out = F.linear(x, self.base_weight, self.bias)
        
        return cheby_out + base_out

class ChebyKAN(nn.Module):
    def __init__(self, in_features=46, hidden_features=64, num_classes=4, degree=5):
        super(ChebyKAN, self).__init__()
        
        self.layer1 = ChebyKANLayer(in_features, hidden_features, degree)
        self.norm = nn.LayerNorm(hidden_features)
        self.drop = nn.Dropout(0.2)
        
        self.layer2 = ChebyKANLayer(hidden_features, hidden_features, degree)
        self.norm2 = nn.LayerNorm(hidden_features)
        
        self.layer3 = ChebyKANLayer(hidden_features, num_classes, degree)
        
        self._print_and_assert_params(in_features, hidden_features, num_classes, degree)

    def _print_and_assert_params(self, in_features, hidden_features, num_classes, degree):
        print("--- ChebyKAN Parameter Breakdown ---")
        total = 0
        for name, param in self.named_parameters():
            if param.requires_grad:
                num_params = param.numel()
                print(f"{name}: {list(param.size())} -> {num_params}")
                total += num_params
        print(f"Total Parameters: {total}")
        
        # For CAN-VTC with 4 classes, expected 44,164.
        if in_features == 46 and hidden_features == 64 and num_classes == 4 and degree == 5:
            assert total == 44164, f"Parameter count mismatch! Expected 44164, got {total}"

    def forward(self, x):
        x = self.layer1(x)
        x = self.norm(x)
        x = self.drop(x)
        
        x = self.layer2(x)
        x = self.norm2(x)
        x = self.drop(x)
        
        x = self.layer3(x)
        return x
