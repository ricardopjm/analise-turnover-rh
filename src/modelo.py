"""Regressao logistica de risco mensal (pessoa-mes) em Python puro, via Newton-Raphson."""
import math
def solve(A, b):
    n = len(A); M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]
        piv = M[i][i]
        for j in range(i, n+1): M[i][j] /= piv
        for r in range(n):
            if r != i:
                f = M[r][i]
                if f:
                    for j in range(i, n+1): M[r][j] -= f*M[i][j]
    return [M[i][n] for i in range(n)]
def inv(A):
    n = len(A); cols = [solve(A, [1.0 if i == j else 0.0 for i in range(n)]) for j in range(n)]
    return [[cols[j][i] for j in range(n)] for i in range(n)]
def logit(X, y, nomes, it=25, ridge=1e-6):
    n, k = len(X), len(X[0]); b = [0.0]*k
    for _ in range(it):
        g = [0.0]*k; H = [[0.0]*k for _ in range(k)]
        for xi, yi in zip(X, y):
            z = sum(bj*xj for bj, xj in zip(b, xi)); p = 1/(1+math.exp(-max(-30, min(30, z)))); w = p*(1-p)
            r = yi - p
            nz = [j for j in range(k) if xi[j]]
            for j in nz:
                g[j] += r*xi[j]
                hj = H[j]; wx = w*xi[j]
                for l in nz: hj[l] += wx*xi[l]
        for j in range(k): H[j][j] += ridge
        step = solve(H, g); b = [bj+s for bj, s in zip(b, step)]
        if max(abs(s) for s in step) < 1e-7: break
    V = inv(H); se = [math.sqrt(V[j][j]) for j in range(k)]
    return [(nomes[j], b[j], se[j], math.exp(b[j]), math.exp(b[j]-1.96*se[j]), math.exp(b[j]+1.96*se[j]), b[j]/se[j]) for j in range(k)]
