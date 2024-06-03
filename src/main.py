from pathlib import Path
import sys
import os
import numpy as np
import pandas as pd
import json
import logging
from datetime import datetime
from collections import defaultdict
from utils import BasicOperationsHelper, MetadataHelper, DatasetHelper, ExtractionHelper, GLMHelper, VisualizationHelper

# Add parent folder of src to path and change cwd
__location__ = Path(__file__).parent.parent
sys.path.append(str(__location__))
os.chdir(__location__)

# Choose params
subject_ids = ["02"]
normalizations = ["no_norm"] # ["min_max", "mean_centered_ch_t", "median_centered_ch_t", "robust_scaling", "no_norm"]
lock_event = "saccade"
meg_channels = [1731, 1921, 2111, 2341, 2511]
timepoint_min = 50
timepoint_max = 250
alphas = [1,10,100,1000,10000,100000,1000000] 
all_sessions_combined = False
pca_components = 4

ann_model = "Resnet50"
module_name = "fc"
batch_size = 32

logger_level=logging.INFO

# Choose Calculations to be performed
create_metadata = False
create_train_test_split = False
create_non_meg_dataset = False
create_meg_dataset = False
extract_features = False
perform_pca = False
train_GLM = False
generate_predictions_with_GLM = False
visualization = True

use_pca_features = True

# Handle logger
logger = logging.getLogger(__name__)
logging.root.handlers = []
filename = (
        "logs/pipeline_" + datetime.now().strftime("%d-%m-%Y_%H-%M-%S") + ".log"
    )
handlers = [logging.StreamHandler()]  # logging.FileHandler(filename=filename, encoding="utf-8", mode="w"),
logging.basicConfig(
    format="[%(asctime)s] [%(name)s] [%(levelname)s] [%(funcName)s] %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    level=logger_level,
    handlers=handlers,
)


for subject_id in subject_ids:
    logger.info(msg=f"Processing subject {subject_id}.")

    ##### Process metadata for subject #####
    if create_metadata:
        metadata_helper = MetadataHelper(subject_id=subject_id, lock_event=lock_event)

        # Read metadata of all available crops/images
        metadata_helper.create_crop_metadata_dict()
        # Read metadata of all available meg datapoints
        metadata_helper.create_meg_metadata_dict()
        # Create combined metadata that only contains timepoints for which crop and meg information exists
        metadata_helper.create_combined_metadata_dict(investigate_missing_data=False)

        logger.info(msg="Metadata created.")

    ##### Create crop and meg dataset based on metadata #####
    if create_non_meg_dataset or create_meg_dataset or create_train_test_split:
        dataset_helper = DatasetHelper(subject_id=subject_id, normalizations=normalizations, chosen_channels=meg_channels, lock_event=lock_event, timepoint_min=timepoint_min, timepoint_max=timepoint_max)

        if create_train_test_split:
            # Create train/test split based on sceneIDs (based on trial_ids)
            dataset_helper.create_train_test_split()

            logger.info(msg="Train/Test split created.")

        if create_non_meg_dataset:
            # Create crop dataset with images as numpy arrays
            dataset_helper.create_crop_dataset()
            # Covert numpy arrays to pytorch tensors
            dataset_helper.create_pytorch_dataset()

            logger.info(msg="Non-MEG datasets created.")

        if create_meg_dataset:
            # Create meg dataset based on split
            dataset_helper.create_meg_dataset()

            logger.info(msg="MEG datasets created.")


    ##### Extract features from crops and perform pca #####
    if extract_features or perform_pca:
        extraction_helper = ExtractionHelper(subject_id=subject_id, pca_components=pca_components, ann_model=ann_model, module_name=module_name, batch_size=batch_size, lock_event=lock_event)

        if extract_features:
            extraction_helper.extract_features()
            logger.info(msg="Features extracted.")

        if perform_pca:
            extraction_helper.reduce_feature_dimensionality(all_sessions_combined=all_sessions_combined)
            logger.info(msg="PCA applied to features.")
        

    ##### Train GLM from features to meg #####
    if train_GLM or generate_predictions_with_GLM:
        glm_helper = GLMHelper(normalizations=normalizations, subject_id=subject_id, chosen_channels=meg_channels, alphas=alphas, timepoint_min=timepoint_min, timepoint_max=timepoint_max, pca_features=use_pca_features, pca_components=pca_components, lock_event=lock_event, ann_model=ann_model, module_name=module_name, batch_size=batch_size)

        # Train GLM
        if train_GLM:
            glm_helper.train_mapping(all_sessions_combined=all_sessions_combined)

            logger.info(msg="GLMs trained.")

        # Generate meg predictions from GLMs
        if generate_predictions_with_GLM:
            glm_helper.predict_from_mapping(store_timepoint_based_losses=False, predict_train_data=False, all_sessions_combined=all_sessions_combined)
            glm_helper.predict_from_mapping(store_timepoint_based_losses=False, predict_train_data=True, all_sessions_combined=all_sessions_combined)

            logger.info(msg="Predictions generated.")

    ##### Visualization #####
    if visualization:
        visualization_helper = VisualizationHelper(normalizations=normalizations, subject_id=subject_id, chosen_channels=meg_channels, lock_event=lock_event, alphas=alphas, timepoint_min=timepoint_min, timepoint_max=timepoint_max, pca_features=use_pca_features, pca_components=pca_components, ann_model=ann_model, module_name=module_name, batch_size=batch_size)

        # Visualize meg data with mne
        #visualization_helper.visualize_meg_epochs_mne()

        # Visualize meg data ERP style
        #visualization_helper.visualize_meg_ERP_style(plot_norms=["no_norm", "mean_centered_ch_t"])  # ,"robust_scaling_ch_t", "z_score_ch_t", "robust_scaling", "z_score"

        # Visualize encoding model performance
        visualization_helper.visualize_self_prediction(var_explained=True, only_self_pred=True, all_sessions_combined=all_sessions_combined)
        visualization_helper.visualize_self_prediction(var_explained=True, only_self_pred=False, all_sessions_combined=all_sessions_combined)

        # Visualize prediction results
        #visualization_helper.visualize_GLM_results(by_timepoints=False, only_distance=False, omit_sessions=[], separate_plots=True)
        #visualization_helper.visualize_GLM_results(only_distance=True, omit_sessions=["4","10"], var_explained=True)
        #visualization_helper.visualize_GLM_results(only_distance=True, omit_sessions=["4","10"], var_explained=False)
        
        # Visualize model perspective (values by timepoint)
        #visualization_helper.visualize_model_perspective(plot_norms=["no_norm"], seperate_plots=False)  # , "no_norm"

        logger.info(msg="Visualization completed.")
        

logger.info(msg="Pipeline completed.")

