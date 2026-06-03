from azure.ai.ml import MLClient, Input
from azure.ai.ml.dsl import pipeline
from azure.ai.ml.entities import Component
from azure.identity import DefaultAzureCredential

# ──────────────────────────────────────────────
# Workspace config — pas deze aan
# ──────────────────────────────────────────────
SUBSCRIPTION_ID = "dba659e6-ef34-4120-8521-21c71238bfeb"
RESOURCE_GROUP  = "azure-project"
WORKSPACE_NAME  = "projectmachinelearning"
COMPUTE_NAME    = "rna-cluster-large"

# ──────────────────────────────────────────────
# Connect to workspace
# ──────────────────────────────────────────────
ml_client = MLClient(
    DefaultAzureCredential(),
    subscription_id=SUBSCRIPTION_ID,
    resource_group_name=RESOURCE_GROUP,
    workspace_name=WORKSPACE_NAME,
)

# ──────────────────────────────────────────────
# Load components
# ──────────────────────────────────────────────
dataprep_component      = ml_client.components.get("dataprep", label="latest")
traintestsplit_component = ml_client.components.get("traintestsplit", label="latest")
training_component      = ml_client.components.get("training", label="latest")

# ──────────────────────────────────────────────
# Data assets
# ──────────────────────────────────────────────
train_sequences   = ml_client.data.get("train_sequences_v2", version="1")
train_labels      = ml_client.data.get("train_labels_v2", version="1")
validation_seqs   = ml_client.data.get("validation_sequences", version="1")

# ──────────────────────────────────────────────
# Pipeline definition
# ──────────────────────────────────────────────
@pipeline(
    name="rna_training_pipeline",
    description="Preprocessing, splitting and training for RNA folding model",
    compute=COMPUTE_NAME,
)
def rna_pipeline(train_sequences_dir, train_labels_dir, validation_sequences_dir):

    # Stap 1: preprocessing
    prep = dataprep_component(
        train_sequences_dir=train_sequences_dir,
        train_labels_dir=train_labels_dir,
        validation_sequences_dir=validation_sequences_dir,
    )

    # Stap 2: train/val split
    split = traintestsplit_component(
        processed_data_path=prep.outputs.output_dir,
    )

    # Stap 3: training
    train = training_component(
        train_path=split.outputs.output_dir,
        val_path=split.outputs.output_dir,
        experiment_name="rna_experiment",
        epochs=1,
    )

    return {"model_output": train.outputs.output_dir}


# ──────────────────────────────────────────────
# Submit pipeline
# ──────────────────────────────────────────────
pipeline_job = rna_pipeline(
    train_sequences_dir=Input(type="uri_folder", path=train_sequences.path),
    train_labels_dir=Input(type="uri_folder", path=train_labels.path),
    validation_sequences_dir=Input(type="uri_folder", path=validation_seqs.path),
)

pipeline_job = ml_client.jobs.create_or_update(pipeline_job, experiment_name="rna_folding")
print(f"Pipeline submitted: {pipeline_job.name}")
print(f"Studio URL: {pipeline_job.studio_url}")