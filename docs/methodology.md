# Methodological Framework & Statistical Definitions

## 1. Principles of Methodological Rigor

The **Brazil Election Insights** platform adheres to strict scientific and empirical principles:

1. **Separation of Signal and Cause**: A statistical outlier is an observation that deviates from the expected central tendency or dispersion of a population. It identifies a phenomenon warranting contextual inquiry (demographic, logistical, or geographic), **never proof of electoral fraud or systemic manipulation**.
2. **Reproducibility**: Every aggregation and statistical test is deterministic, using versioned inputs and standardized formulas implemented in Python, Polars, SciPy, and DuckDB.
3. **Traceability**: All calculated indicators link directly back to verified official TSE Boletim de Urna records.

---

## 2. Electoral Metrics and Formulas

### Turnout and Abstention Indicators
For any geographic or administrative unit $U$ (National, State, Municipality, or Section):

$$\text{Taxa de Comparecimento (\%)} = \frac{\sum_{s \in U} \text{actual\_turnout}_s}{\sum_{s \in U} \text{eligible\_voters}_s} \times 100$$

$$\text{Taxa de Abstenção (\%)} = \frac{\sum_{s \in U} \text{abstentions}_s}{\sum_{s \in U} \text{eligible\_voters}_s} \times 100$$

Where $\text{eligible\_voters}_s = \text{actual\_turnout}_s + \text{abstentions}_s$.

### Vote Share Indicators
- **Percentual de Votos Válidos (Vote Share)**:
  $$\text{Share}_{\text{cand}} = \frac{\text{Votos}_{\text{cand}}}{\sum_{\text{Nominal}} \text{Votos} + \sum_{\text{Legenda}} \text{Votos}} \times 100$$

- **Taxa de Votos em Branco e Nulos**:
  $$\text{Taxa Brancos (\%)} = \frac{\text{Votos em Branco}}{\text{Comparecimento Total}} \times 100$$
  $$\text{Taxa Nulos (\%)} = \frac{\text{Votos Nulos}}{\text{Comparecimento Total}} \times 100$$

---

## 3. Anomaly Detection Methods

### 3.1 Z-Score (Parametric Deviation)
- **Assumption**: Metric follows an approximately normal distribution.
- **Formula**:
  $$Z_i = \frac{X_i - \mu}{\sigma}$$
  Where $\mu$ is the empirical mean and $\sigma$ is the standard deviation.
- **Default Threshold**: $|Z_i| \ge 3.0$ (observations beyond 3 standard deviations, corresponding to $p < 0.0027$ under normality).
- **Limitations**: Sensitive to extreme skewness; best suited for homogeneous regional strata.

### 3.2 Interquartile Range — IQR (Non-Parametric)
- **Assumption**: Robust against non-normal or skewed distributions.
- **Formula**:
  $$\text{IQR} = Q_3 - Q_1$$
  $$\text{Limiar Superior} = Q_3 + k \times \text{IQR}$$
  $$\text{Limiar Inferior} = Q_1 - k \times \text{IQR}$$
  Where $k = 1.5$ (mild outlier) or $k = 3.0$ (extreme outlier).
- **Application**: Ideal for municipal abstention rates where distributions often display long right tails.

### 3.3 Isolation Forest (Multivariate)
- **Assumption**: Outliers are few and distinct in multi-dimensional feature space.
- **Features Used**: `[turnout_rate_pct, abstention_rate_pct, valid_vote_rate_pct]`.
- **Implementation**: Ensembles of random isolation trees (`scikit-learn.ensemble.IsolationForest`).
- **Contamination**: Default $1\%$ ($\nu = 0.01$).
