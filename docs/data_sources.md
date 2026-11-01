# Official Data Sources & Provenance

## 1. Primary Source

All electoral data ingested by **Brazil Election Insights** is published by the **Tribunal Superior Eleitoral (TSE)** via the official Brazilian Open Data Portal (*Dados Abertos TSE*):

- **Portal URL**: [https://dadosabertos.tse.jus.br/](https://dadosabertos.tse.jus.br/)
- **Dataset**: *Boletim de Urna na Web (BWeb)*
- **Dataset Description**: Official polling station ballot logs (*Boletins de Urna*) recorded by individual electronic voting machines (*Urnas Eletrônicas*).
- **Official Documentation**: `_leiame-boletimurnaweb.pdf` (preserved in `data/bronze/tse/2026/`).

---

## 2. File Organization and Naming Convention

TSE distributes BWeb datasets as zip or direct CSV exports per State/UF and round:

- **1º Turno (First Round)**:
  - Pattern: `bweb_1t_{UF}_{DDMMYYYYHHMM}.csv`
  - Example: `bweb_1t_AC_051020261403.csv`, `bweb_1t_ZZ_051020261403.csv`
  - Target Path: `data/bronze/tse/2026/1t/`
  - Scope: Federal, State, and District elections (President, Governor, Senator, Federal Deputy, State/District Deputy).

- **2º Turno (Second Round)**:
  - Pattern: `bweb_2t_{UF}_{DDMMYYYYHHMM}.csv`
  - Example: `bweb_2t_AC_261020260742.csv`, `bweb_2t_ZZ_261020260742.csv`
  - Target Path: `data/bronze/tse/2026/2t/`
  - Scope: Runoff elections (President, Governor).

---

## 3. Data Integrity & Provenance Rules

1. **Bronze Immutability**: Source files placed in `data/bronze/` are never modified, edited, or rewritten.
2. **Local SHA-512 Verification**: Every imported CSV has its SHA-512 cryptographic hash calculated and stored in an immutable JSON manifest (`data/metadata/manifests/manifest_YYYY_Rt.json`).
3. **Official vs. Local Checksums**:
   - *Official Checksums*: Checksums published by TSE on the Open Data portal or accompanying `.sha512` files when available.
   - *Local Checksums*: SHA-512 hashes calculated directly from the raw disk bytes upon ingestion.
4. **Audit Trail**: Every processed record in the Silver and Gold layers maintains references to its source file name and processing batch timestamp.
