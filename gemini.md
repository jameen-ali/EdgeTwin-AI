# EdgeTwin AI Context

1. **Project Identity**: EdgeTwin AI is an AI-powered predictive maintenance platform using digital twins and edge intelligence.
2. **Pipeline**: Wokwi/ESP32 -> Edge -> MQTT -> API Ingest -> DB / ML Features -> Inference (Risk/Anomaly) -> Health Engine -> Twin Service -> React Dashboard.
3. **Labels**:
   - `[FACT]`: Verified from a source.
   - `[DECISION]`: Our design choice.
   - `[PROPOSED]`: Proposed system contribution.
   - `[ASSUMPTION]`: Unverified, must be checked.
4. **Folder Map**:
   - `api/`: Backend service
   - `dashboard/`: Frontend UI
   - `data/`: Datasets (raw, interim, processed)
   - `docs/`: Documentation
   - `edge/`: Firmware
   - `ml/`: Machine learning pipeline
   - `mlops/`: MLOps scripts/configs
   - `notebooks/`: Jupyter notebooks
   - `simulation/`: Virtual edge and scenario spec
   - `tests/`: Test suites
5. **Core Engineering Principles**: Reproducibility, no secrets, no fabricated data, tests required, validate before claiming done.
6. **Mandatory Reading Order**:
   - `rules.md`
   - `tasks.md`
   - `memory.md`
7. **Rule 1**: Work on one task at a time.
8. **Rule 2**: Update `tasks.md` and `memory.md` at the end of every completed task.
