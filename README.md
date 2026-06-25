# Mass Spectrometry Quality Control AI Agent

An end-to-end, event-driven Machine Learning Operations (MLOps) pipeline designed for real-time manufacturing quality control. This system simulates high-throughput sensor data, performs binary classification to detect compound anomalies, and leverages a local LLM to generate automated root-cause analysis for rejected batches.
Architecture & Tech Stack

    Data Engineering: Rust, Apache Kafka, PostgreSQL

    Machine Learning: AutoGluon (AutoML), MLflow, Scikit-learn

    Generative AI: Llama 3 (via Ollama), Pydantic AI

    Orchestration & Automation: n8n, Docker Compose

## Core Components
1. High-Throughput Data Ingestion (Rust & Kafka)

    Data Simulator: A highly concurrent Rust application that generates synthetic 3-sigma aggregates of mass spectra data.

    Buffer Architecture: Utilizes Apache Kafka as a message broker to decouple data generation from storage. This guarantees high-throughput ingestion and prevents PostgreSQL database bottlenecking during massive manufacturing spikes.

2. Event-Driven Inference & AutoML (Python)

    Model Pipeline: Evaluates incoming compounds as 1 (Pass) or 0 (Fail/Anomaly).

    AutoML Integration: Leverages AutoGluon to automatically train, tune, and select the highest-performing classification model.

    Model Registry: MLflow tracks all experiments, hyperparameters, and model versions to ensure full reproducibility and lifecycle management.

    Batch Processing: Capable of running both real-time endpoint inference and scheduled batch retraining to prevent model drift.

3. Automated Root-Cause Analysis (GenAI)

    When the ML model flags a compound as anomalous (0), the pipeline automatically triggers a local instance of Llama 3 (managed via Pydantic AI).

    The LLM ingests the raw mass spectrometry data and generates a human-readable explanation of the failure mode, keeping sensitive manufacturing data 100% on-premises.

4. Workflow Orchestration (n8n)

    Replaces rigid polling with an event-driven webhook architecture.

    Monitors PostgreSQL for new sample INSERT events and instantly triggers the Python ML prediction API, routing the output to the appropriate alerting dashboard.

## MLOps Highlights

    Scalability: Kafka decouples ingestion from processing, allowing the database and ML inference server to scale independently.

    Security: Local deployment of Llama 3 ensures zero data leakage of proprietary chemical spectra.

    Automation: n8n and AutoGluon eliminate manual intervention in both workflow routing and algorithm tuning.