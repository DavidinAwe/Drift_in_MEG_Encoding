import os
import json
import h5py
import pickle
import pandas as pd
import numpy as np
import imageio
import mne
import matplotlib.pyplot as plt
from collections import defaultdict
from typing import Tuple, Dict

# ANN specific imports
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from thingsvision import get_extractor

from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error

class BasicOperationsHelper:
    def __init__(self, subject_id: str = "02"):
        self.subject_id = subject_id
        self.session_ids_char = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
        self.session_ids_num = [str(session_id) for session_id in range(1,11)]


    def map_session_letter_id_to_num(self, session_id_letter: str) -> str:
        """
        Helper function to map the character id from a session to its number id.
        For example: Input "a" will return "1".
        """
        # Create mapping
        session_mapping = {}
        for num in range(1,11):
            letter = self.session_ids_char[num-1]
            session_mapping[letter] = str(num)
        # Map letter to num
        session_id_num = session_mapping[session_id_letter]

        return session_id_num


    def read_dict_from_json(self, type_of_content: str) -> dict:
        """
        Helper function to read json files into dicts.

        Allowed Parameters: ["combined_metadata", "meg_metadata", "crop_metadata", "mse_losses"]
        """
        valid_types = ["combined_metadata", "meg_metadata", "crop_metadata", "mse_losses"]
        if type_of_content not in valid_types:
            raise ValueError(f"Function read_dict_from_json called with unrecognized type {type_of_content}.")

        if type_of_content == "mse_losses":
            file_path = f"data_files/mse_losses/{self.ann_model}/{self.module_name}/subject_{self.subject_id}/mse_losses_dict.json"
        else:
            file_path = f"data_files/metadata/{type_of_content}/subject_{self.subject_id}/{type_of_content}_dict.json"
        
        try:
            with open(file_path, 'r') as data_file:
                data_dict = json.load(data_file)
            return data_dict
        except FileNotFoundError:
            raise FileNotFoundError(f"In Function read_dict_from_json: The file {file_path} does not exist.")

        return data_dict


    def save_dict_as_json(self, type_of_content: str, dict_to_store: dict) -> None:
        """
        Helper function to store dicts as json files.

        Allowed Parameters: ["combined_metadata", "meg_metadata", "crop_metadata", "mse_losses"]
        """
        valid_types = ["combined_metadata", "meg_metadata", "crop_metadata", "mse_losses"]
        if type_of_content not in valid_types:
            raise ValueError(f"Function save_dict_as_json called with unrecognized type {type_of_content}.")

        if type_of_content == "mse_losses":
            storage_folder = f"data_files/mse_losses/{self.ann_model}/{self.module_name}/subject_{self.subject_id}"
        else:
            storage_folder = f'data_files/metadata/{type_of_content}/subject_{self.subject_id}'
        if not os.path.exists(storage_folder):
            os.makedirs(storage_folder)
        json_storage_file = f"{type_of_content}_dict.json"
        json_storage_path = os.path.join(storage_folder, json_storage_file)

        with open(json_storage_path, 'w') as file:
            # Serialize and save the dictionary to the file
            json.dump(dict_to_store, file, indent=4)


    def export_split_data_as_file(self, session_id: str, type_of_content: str, array_dict: Dict[str, np.ndarray], ann_model: str = None, module: str = None) -> None:
        """
        Helper function to export train/test numpy arrays as .npz or .pt files.

        Parameters: 
            session_id (str): id of session that the arrays belong to
            type_of_content (str): Type of data in arrays. Allowed values: ["trial_splits", "crop_data", "meg_data", "torch_dataset", "ann_features"]
            np_array (Dict[str, ndarray]): Arrays in format split, array. split is "train" or "test".
        """
        valid_types = ["trial_splits", "crop_data", "meg_data", "torch_dataset", "ann_features"]
        if type_of_content not in valid_types:
            raise ValueError(f"Function export_split_data_as_file called with unrecognized type {type_of_content}.")

        # Set file type
        if type_of_content == "torch_dataset":
            file_type = ".pt"
        else:
            file_type = ".npy"
        
        # Add additional folder for model type and extraction layer for ann_features
        if type_of_content == "ann_features":
            additional_folders = f"/{ann_model}/{module}/"
        else:
            additional_folders = "/"

        # Export train/test split arrays to .npz
        for split in array_dict:
            save_folder = f"data_files/{type_of_content}{additional_folders}subject_{self.subject_id}/session_{session_id}/{split}"  
            save_file = f"{type_of_content}{file_type}"
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)
            save_path = os.path.join(save_folder, save_file)

            if file_type == ".npy":
                np.save(save_path, array_dict[split])
            else:
                torch.save(array_dict[split], save_path)


    
    def load_split_data_from_file(self, session_id_num: str, type_of_content: str, ann_model: str = None, module: str = None) -> dict:
        """
        Helper function to load the split for a given session.

        Parameters: 
            session_id_num (str): id of session that the arrays belong to
            type_of_content (str): Type of data in arrays. Allowed values: ["trial_splits", "crop_data", "meg_data", "torch_dataset", "ann_features"]
        """
        valid_types = ["trial_splits", "crop_data", "meg_data", "torch_dataset", "ann_features"]
        if type_of_content not in valid_types:
            raise ValueError(f"Function load_split_data_from_file called with unrecognized type {type_of_content}.")

        if type_of_content == "torch_dataset":
            file_type = ".pt"
        else:
            file_type = ".npy"

        # Add additional folder for model type and extraction layer for ann_features
        if type_of_content == "ann_features":
            additional_folders = f"/{ann_model}/{module}/"
        else:
            additional_folders = "/"

        split_dict = {}
        for split in ["train", "test"]:
            # Load split trial array
            split_path = f"data_files/{type_of_content}{additional_folders}subject_{self.subject_id}/session_{session_id_num}/{split}/{type_of_content}{file_type}"  
            if file_type == ".npy":
                split_data = np.load(split_path)
            else:
                split_data = torch.load(split_path)
            split_dict[split] = split_data

        return split_dict

    
    def save_plot_as_file(self, plt, plot_folder: str, plot_file: str):
        """
        Helper function to save a plot as file.
        """
        if not os.path.exists(plot_folder):
            os.makedirs(plot_folder)
        plot_path = os.path.join(plot_folder, plot_file)
        plt.savefig(plot_path)
        plt.close()


    def normalize_array(self, data):
        """
        Helper function to normalize meg data across a session.
        """
        data_min = data.min()
        data_max = data.max()
        normalized_data = (data - data_min) / (data_max - data_min)

        return normalized_data



class MetadataHelper(BasicOperationsHelper):
    def __init__(self, subject_id: str = "02"):
        super().__init__(subject_id)

        self.crop_metadata_path = f"/share/klab/psulewski/psulewski/active-visual-semantics/input/fixation_crops/avs_meg_fixation_crops_scene_224/metadata/as{subject_id}_crops_metadata.csv"
        self.meg_metadata_folder = f"/share/klab/datasets/avs/population_codes/as{subject_id}/sensor/filter_0.2_200"


    def recursive_defaultdict(self) -> dict:
        return defaultdict(self.recursive_defaultdict)


    def create_combined_metadata_dict(self) -> None:
        """
        Creates the combined metadata dict with timepoints that can be found in both meg and crop metadata for the respective session and trial.
        """

        # Read crop metadata from json
        crop_metadata = self.read_dict_from_json(type_of_content="crop_metadata")
        # Read meg metadata from json
        meg_metadata = self.read_dict_from_json(type_of_content="meg_metadata")

        # Store information about timepoints that are present in both meg and crop data

        # Use defaultdict to automatically create missing keys
        combined_metadata_dict = self.recursive_defaultdict()

        meg_index = 0
        for session_id in meg_metadata["sessions"]:
            for trial_id in meg_metadata["sessions"][session_id]["trials"]:
                for timepoint_id in meg_metadata["sessions"][session_id]["trials"][trial_id]["timepoints"]:
                    # For each timepoint in the meg metadata: Check if this timepoint is in the crop metadata and if so store it
                    try:
                        crop_identifier = crop_metadata["sessions"][session_id]["trials"][trial_id]["timepoints"][timepoint_id].get("crop_identifier", None)
                        sceneID = crop_metadata["sessions"][session_id]["trials"][trial_id]["timepoints"][timepoint_id].get("sceneID", None)
                        combined_metadata_dict["sessions"][session_id]["trials"][trial_id]["timepoints"][timepoint_id]["crop_identifier"] = crop_identifier
                        combined_metadata_dict["sessions"][session_id]["trials"][trial_id]["timepoints"][timepoint_id]["sceneID"] = sceneID
                        combined_metadata_dict["sessions"][session_id]["trials"][trial_id]["timepoints"][timepoint_id]["meg_index"] = meg_index
                    except:
                        pass
                    meg_index += 1
        
        # Export dict to json 
        self.save_dict_as_json(type_of_content="combined_metadata", dict_to_store=combined_metadata_dict)


    def create_meg_metadata_dict(self) -> None:
        """
        Creates the meg metadata dict for the participant and stores it.
        """

        data_dict = {"sessions": {}}
        # Read metadata for each session from csv
        for session_id_letter in self.session_ids_char:
            # Build path to session metadata file
            meg_metadata_file = f"as{self.subject_id}{session_id_letter}_et_epochs_metadata_fixation.csv"
            meg_metadata_path = os.path.join(self.meg_metadata_folder, meg_metadata_file)

            session_id_num = self.map_session_letter_id_to_num(session_id_letter)

            data_dict["sessions"][session_id_num] = {}

            # Read metadata from csv 
            df = pd.read_csv(meg_metadata_path, delimiter=";")

            # Create ordered dict
            data_dict["sessions"][session_id_num]["trials"] = {}

            for index, row in df.iterrows():
                trial_id = int(row["trial"])
                timepoint = row["time_in_trial"]
                
                # Create dict to store values for current trial if this is the first timepoint in the trial
                if trial_id not in data_dict["sessions"][session_id_num]["trials"].keys():
                    data_dict["sessions"][session_id_num]["trials"][trial_id] = {"timepoints": {}}

                # Store availability of current timepoint in trial
                data_dict["sessions"][session_id_num]["trials"][trial_id]["timepoints"][timepoint] = {"meg":True}

        # Export dict to json 
        self.save_dict_as_json(type_of_content="meg_metadata", dict_to_store=data_dict)


    def create_crop_metadata_dict(self) -> None:
        """
        Creates the crop metadata dict for the participant and stores it.
        """

        # Read data from csv and set index to crop filename (crop_identifier before .png)
        df = pd.read_csv(self.crop_metadata_path, index_col = 'crop_filename')

        # Remove rows/fixations without crop identifiers
        df = df[df.index.notnull()]

        num_sessions = df["session"].max() #10 sessions for subj 2

        # Create ordered dict
        data_dict = {"sessions": {}}

        for nr_session in range(1,num_sessions+1):
            # Create dict for this session
            data_dict["sessions"][nr_session] = {}

            # Filter dataframe by session 
            session_df = df[df["session"] == nr_session]
            # Filter dataframe by type of recording (we are only interested in scene recordings, in the meg file I am using there is no data for caption of microphone recordings (or "nothing" recordings))
            session_df = session_df[session_df["recording"] == "scene"]

            # Get list of all trials in this session
            trial_numbers = list(map(int, set(session_df["trial"].tolist())))

            # Create dict for trials in this session
            data_dict["sessions"][nr_session]["trials"] = {}

            # For each trial in the session
            for nr_trial in trial_numbers:
                # Filter session dataframe by trial
                trial_df = session_df[session_df["trial"] == nr_trial]

                # Create dict for this trial
                data_dict["sessions"][nr_session]["trials"][nr_trial] = {}

                # Get list of all timepoints in this trial
                timepoints = trial_df["time_in_trial"].tolist()

                # Create dict for timepoints in this trial
                data_dict["sessions"][nr_session]["trials"][nr_trial]["timepoints"] = {}

                # For each timepoint in this trial
                for timepoint in timepoints:
                    # Filter trial dataframe by timepoint
                    timepoint_df = trial_df[trial_df["time_in_trial"] == timepoint]

                    # get sceneID for this timepoint
                    sceneID = timepoint_df['sceneID'].iloc[0]

                    # Create dicts for this timepoint
                    data_dict["sessions"][nr_session]["trials"][nr_trial]["timepoints"][timepoint] = {}

                    # Fill in crop identifier value (here the index without ".png") in main data dict for this timepoint, as well as scene id and space for meg data
                    # metadata
                    data_dict["sessions"][nr_session]["trials"][nr_trial]["timepoints"][timepoint]["crop_identifier"] = timepoint_df.index.tolist()[0][:-4]  # slice with [0] to get single element instead of list, then slice off ".png" at the end
                    data_dict["sessions"][nr_session]["trials"][nr_trial]["timepoints"][timepoint]["sceneID"] = sceneID
        
        # Export dict to json 
        self.save_dict_as_json(type_of_content="crop_metadata", dict_to_store=data_dict)


        
class DatasetHelper(BasicOperationsHelper):
    def __init__(self, subject_id: str = "02"):
        super().__init__(subject_id)

        self.crop_metadata_path = f"/share/klab/psulewski/psulewski/active-visual-semantics/input/fixation_crops/avs_meg_fixation_crops_scene_224/metadata/as{subject_id}_crops_metadata.csv"
        self.meg_metadata_folder = f"/share/klab/datasets/avs/population_codes/as{subject_id}/sensor/filter_0.2_200"


    def create_crop_dataset(self) -> None:
        """
        Creates the crop dataset with all crops in the combined_metadata (crops for which meg data exists)
        """

        # Read combined metadata from json
        combined_metadata = self.read_dict_from_json(type_of_content="combined_metadata")

        # Define path to read crops from
        crop_folder_path = f"/share/klab/psulewski/psulewski/active-visual-semantics/input/fixation_crops/avs_meg_fixation_crops_scene_224/crops/as{self.subject_id}"

        # For each session: create crop datasets based on respective splits
        for session_id in self.session_ids_num:
            # Get train/test split based on trials (based on scenes)
            trials_split_dict = self.load_split_data_from_file(session_id_num=session_id, type_of_content="trial_splits")

            crop_split = {"train": [], "test": []}
            for trial_id in combined_metadata["sessions"][session_id]["trials"]:
                # Check if trial belongs to train or test split
                if trial_id in trials_split_dict["train"]:
                    trial_type = "train"
                elif trial_id in trials_split_dict["test"]:
                    trial_type = "test"
                else:
                    raise ValueError(f"Trial_id {trial_id} neither in train nor test split.")
                for timepoint_id in combined_metadata["sessions"][session_id]["trials"][trial_id]["timepoints"]:
                    # Extract image for every epoch/fixation (if there is both crop and metadata for the timepoint)
                    if timepoint_id in combined_metadata["sessions"][session_id]["trials"][trial_id]["timepoints"]:
                        # Get crop path
                        crop_filename = ''.join([combined_metadata["sessions"][session_id]["trials"][trial_id]["timepoints"][timepoint_id]["crop_identifier"], ".png"])
                        crop_path = os.path.join(crop_folder_path, crop_filename)

                        # Read crop as array and concat
                        crop = imageio.imread(crop_path)
                        crop_split[trial_type].append(crop)
            # Convert to numpy array
            for split in crop_split:
                crop_split[split] = np.stack(crop_split[split], axis=0)

            # Export numpy array to .npz
            self.export_split_data_as_file(session_id=session_id, 
                                        type_of_content="crop_data",
                                        array_dict=crop_split)


    def create_meg_dataset(self) -> None:
        """
        Creates the crop dataset with all crops in the combined_metadata (crops for which meg data exists)
        """

        # Read combined and meg metadata from json
        combined_metadata = self.read_dict_from_json(type_of_content="combined_metadata")
        meg_metadata = self.read_dict_from_json(type_of_content="meg_metadata")

        meg_data_folder = f"/share/klab/datasets/avs/population_codes/as{self.subject_id}/sensor/filter_0.2_200"

        for session_id_char in self.session_ids_char:
            session_id_num = self.map_session_letter_id_to_num(session_id_char)
            # Load session MEG data from .h5
            meg_data_file = f"as{self.subject_id}{session_id_char}_population_codes_fixation_500hz_masked_False.h5"
            with h5py.File(os.path.join(meg_data_folder, meg_data_file), "r") as f:
                meg_data = {}
                meg_data["grad"] = f['grad']['onset']  # shape participant 2, session a (2874, 204, 601)
                meg_data["mag"] = f['mag']['onset']  # shape participant 2, session a (2874, 102, 601)
    
                # Normalize grad and mag independently
                meg_data["grad"] = self.normalize_array(np.array(meg_data['grad']))
                meg_data["mag"] = self.normalize_array(np.array(meg_data['mag']))

                # Combine grad and mag data
                combined_meg = np.concatenate([meg_data["grad"], meg_data["mag"]], axis=1) #(2874, 306, 601)
    
                # Split meg data 
                # Get train/test split based on trials (based on scenes)
                trials_split_dict = self.load_split_data_from_file(session_id_num=session_id_num, type_of_content="trial_splits")

                meg_split = {"train": [], "test": []}
                # Iterate through meg metadata for simplicity with indexing
                index = 0
                for trial_id in meg_metadata["sessions"][session_id_num]["trials"]:
                    if trial_id in trials_split_dict["train"]:
                        trial_type = "train"
                    elif trial_id in trials_split_dict["test"]:
                        trial_type = "test"
                    else:
                        # Raise error if the trial is in neither split, but is in the combined metadata (in this case it should be there)
                        if trial_id in combined_metadata["sessions"][session_id_num]["trials"]:
                            raise ValueError(f"Session {session_id_num}: Trial_id {trial_id} neither in train nor test split.")
                        # Otherwise skip this trial
                        else:
                            index += 1
                            continue
                    for timepoint in meg_metadata["sessions"][session_id_num]["trials"][trial_id]["timepoints"]:
                        # Check if there is both crop and metadata for the timepoint
                        if timepoint in combined_metadata["sessions"][session_id_num]["trials"][trial_id]["timepoints"]:
                            # Assign to split
                            meg_split[trial_type].append(combined_meg[index])
                        # Advance index
                        index += 1

                # Export meg dataset arrays to .npz
                self.export_split_data_as_file(session_id=session_id_num, 
                                            type_of_content="meg_data",
                                            array_dict=meg_split)


    def create_train_test_split(self):
        """
        Creates train/test split of trials based on scene_ids.
        """
        # Read combined metadata from json
        combined_metadata = self.read_dict_from_json(type_of_content="combined_metadata")

        # Prepare splits for all sessions: count scenes
        scene_ids = {session_id: {} for session_id in combined_metadata["sessions"]}
        trial_ids = {session_id: [] for session_id in combined_metadata["sessions"]}
        num_datapoints = {session_id: 0 for session_id in combined_metadata["sessions"]}
        for session_id in combined_metadata["sessions"]:
            for trial_id in combined_metadata["sessions"][session_id]["trials"]:
                # Store trials in session for comparison with scenes
                trial_ids[session_id].append(trial_id)
                for timepoint in combined_metadata["sessions"][session_id]["trials"][trial_id]["timepoints"]:
                    # get sceneID of current timepoint
                    scene_id_current = combined_metadata["sessions"][session_id]["trials"][trial_id]["timepoints"][timepoint]["sceneID"]
                    # First occurance of the scene? Store its occurange with the corresonding trial
                    if scene_id_current not in scene_ids[session_id]:
                        scene_ids[session_id][scene_id_current] = {"trials": [trial_id]}
                    # SceneID previously occured in another trial, but this trial is not stored yet: store it under the scene_id aswell
                    elif trial_id not in scene_ids[session_id][scene_id_current]["trials"]:
                        scene_ids[session_id][scene_id_current]["trials"].append(trial_id)

                    # Count total datapoints/timepoints/fixations in combined metadata in session
                    num_datapoints[session_id] += 1

        # Create splits for each session
        for session_id in combined_metadata["sessions"]:
            # Debugging: Identical number of trials and scenes in this session?
            num_scenes = len(scene_ids[session_id])  # subject 2, session a: 300 
            num_trials = len(trial_ids[session_id])
            assert num_scenes == num_trials, f"Session {session_id}: Number of trials and number of scenes is not identical. Doubled scenes need to be considered"

            # Choose scene_ids for 80/20 split
            num_trials_train = int(num_trials*0.8)
            num_trials_test = num_trials - num_trials_train

            # Split based on scene ids, but trial information is sufficient to identify datapoint
            train_split_trials = []
            test_split_trials = []
            # Create split sceneID (by ordering the trials by scenes, trials that belong to the same scene will most likely be in the same split)
            index = 0
            for scene_id in scene_ids[session_id]:
                for trial_id in scene_ids[session_id][scene_id]["trials"]:
                    # Each unique combination is one point in the dataset
                    if index < num_trials_train:
                        train_split_trials.append(trial_id)
                    else:
                        test_split_trials.append(trial_id)
                    index += 1

            # To-do: Make sure that scenes only double in the same split

            # Debugging
            """
            if session_id == "1":
                print(f"Session {session_id}: len train_split_trials: {len(train_split_trials)}")
                print(f"Session {session_id}: len test_split_trials: {len(test_split_trials)}")
                print(f"Session {session_id}: Total number of trials in train+test dataset: {len(train_split_trials) + len(test_split_trials)}")
                print(f"Session {session_id}: Total number of trials in session: {num_trials}")
                print(f"Session {session_id}: Total number of datapoints in session: {num_datapoints[session_id]}")
            """

            # Export trial_split arrays to .npz
            split_dict = {"train": train_split_trials, "test": test_split_trials}
            self.export_split_data_as_file(session_id=session_id, 
                                        type_of_content="trial_splits",
                                        array_dict=split_dict)


    def create_pytorch_dataset(self):
        """
        Creates pytorch datasets from numpy image datasets.
        """
        
        for session_id_num in self.session_ids_num:
            # Load numpy datasets for session
            crop_ds = self.load_split_data_from_file(session_id_num=session_id_num, type_of_content="crop_data")

            # Create torch datasets with helper 
            torch_dataset = {}
            torch_dataset["train"] = DatasetHelper.TorchDatasetHelper(crop_ds['train'])
            torch_dataset["test"] = DatasetHelper.TorchDatasetHelper(crop_ds['test'])

            # Store datasets
            self.export_split_data_as_file(session_id=session_id_num, type_of_content="torch_dataset", array_dict=torch_dataset)


    class TorchDatasetHelper(Dataset):
        """
        Inner class to create Pytorch dataset from numpy arrays (images).
        """
        def __init__(self, numpy_array, transform=None):
            """
            Args:
                numpy_array (numpy.ndarray): A Numpy array of images (should be in CHW format if channels are present)
                transform (callable, optional): Optional transform to be applied on a sample.
            """
            self.numpy_array = numpy_array
            if transform is None:
                self.transform = transforms.Compose([transforms.ToTensor(),])  # Convert numpy arrays to torch tensors
            else:
                self.transform = transform

        def __len__(self):
            return len(self.numpy_array)

        def __getitem__(self, idx):
            image = self.numpy_array[idx]

            if self.transform:
                image = self.transform(image)

            # Since no labels are associated, we only return the image
            return image



class ExtractionHelper(BasicOperationsHelper):
    def __init__(self, subject_id: str = "02", ann_model: str = "Resnet50", module_name : str = "fc", batch_size: int = 32):
        super().__init__(subject_id)

        self.ann_model = ann_model
        self.module_name = module_name  # Name of Layer to extract features from
        self.batch_size = batch_size

    
    def extract_features(self):
        """
        Extracts features from crop datasets over all sessions for a subject.
        """
        # Load model
        model_name = f'{self.ann_model}_ecoset'
        source = 'custom'
        device = 'cuda'

        extractor = get_extractor(
            model_name=model_name,
            source=source,
            device=device,
            pretrained=True
        )

        for session_id_num in self.session_ids_num:
            # Load torch datasets for session
            torch_crop_ds = self.load_split_data_from_file(session_id_num=session_id_num, type_of_content="torch_dataset")

            # Create a DataLoader to handle batching
            model_input = {}
            model_input["train"] =  DataLoader(torch_crop_ds["train"], batch_size=self.batch_size, shuffle=False)
            model_input["test"] = DataLoader(torch_crop_ds["test"], batch_size=self.batch_size, shuffle=False)
    
            features_split = {}
            for split in ["train", "test"]:
                # Extract features
                features_split[split] = extractor.extract_features(
                    batches=model_input[split],
                    module_name=self.module_name,
                    flatten_acts=True  # flatten 2D feature maps from convolutional layer
                )

                # Debugging
                if session_id_num == "1":
                    print(f"Session {session_id_num}: {split}_features.shape: {features_split[split].shape}")

            # Export numpy array to .npz
            self.export_split_data_as_file(session_id=session_id_num, type_of_content="ann_features", array_dict=features_split, ann_model=self.ann_model, module=self.module_name)



class GLMHelper(ExtractionHelper):
    def __init__(self, subject_id: str = "02"):
        super().__init__(subject_id=subject_id)


    def train_mapping(self):
        """
        Trains a mapping from ANN features to MEG data over all sessions.
        """
        for session_id_num in self.session_ids_num:
            # Get ANN features for session
            ann_features = self.load_split_data_from_file(session_id_num=session_id_num, type_of_content="ann_features", ann_model=self.ann_model, module=self.module_name)

            # Get MEG data for sesssion
            meg_data = self.load_split_data_from_file(session_id_num=session_id_num, type_of_content="meg_data")

            X_train, Y_train = ann_features['train'], meg_data['train']

            # Initialize Helper class
            ridge_model = GLMHelper.MultiDimensionalRidge(alpha=0.5)

            # Fit model on train data
            ridge_model.fit(X_train, Y_train)

            # Store trained models as pickle
            save_folder = f"data_files/GLM_models/{self.ann_model}/{self.module_name}/subject_{self.subject_id}/session_{session_id_num}"  
            save_file = "GLM_models.pkl"
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)
            save_path = os.path.join(save_folder, save_file)

            with open(save_path, 'wb') as file:
                pickle.dump(ridge_model.models, file)

        
    def predict_from_mapping(self):
        """
        Based on the trained mapping for each session, predicts MEG data over all sessions from their respective test features.
        """
        mse_session_losses = {"session_mapping": {}}
        for session_id_model in self.session_ids_num:
            mse_session_losses["session_mapping"][session_id_model] = {"session_pred": {}}
            # Get trained ridge regression model for this session
            # Load ridge model
            storage_folder = f"data_files/GLM_models/{self.ann_model}/{self.module_name}/subject_{self.subject_id}/session_{session_id_model}"  
            storage_file = "GLM_models.pkl"
            storage_path = os.path.join(storage_folder, storage_file)
            with open(storage_path, 'rb') as file:
                ridge_models = pickle.load(file)
            
            # Initialize MultiDim GLM class with stored models
            ridge_model = GLMHelper.MultiDimensionalRidge(alpha=0.5, models=ridge_models)

            # Generate predictions for test features over all sessions and evaluate them 
            for session_id_pred in self.session_ids_num:
                # Get ANN features and MEG data for session where predictions are to be evaluated
                ann_features = self.load_split_data_from_file(session_id_num=session_id_pred, type_of_content="ann_features", ann_model=self.ann_model, module=self.module_name)
                meg_data = self.load_split_data_from_file(session_id_num=session_id_pred, type_of_content="meg_data")
                X_test, Y_test = ann_features['test'], meg_data['test']

                # Generate predictions
                predictions = ridge_model.predict(X_test)

                # Calculate the mean squared error across all flattened features and timepoints
                mse = mean_squared_error(Y_test.reshape(-1), predictions.reshape(-1))

                # Save loss
                mse_session_losses["session_mapping"][session_id_model]["session_pred"][session_id_pred] = mse

        # Store loss dict
        self.save_dict_as_json(type_of_content="mse_losses", dict_to_store=mse_session_losses)


    class MultiDimensionalRidge:
        """
        Inner class to apply Ridge Regression over all timepoints. Enables training and prediction, as well as initialization of random weights for baseline comparison.
        """
        def __init__(self, alpha=0.5, models=[], random_weights=False):
            self.alpha = alpha
            self.random_weights = random_weights
            self.models = models  # Standardly initialized as empty list, otherwise with passed, previously trained models

        def fit(self, X=None, Y=None):
            n_features = X.shape[1]
            n_sensors = Y.shape[1]
            n_timepoints = Y.shape[2]
            self.models = [Ridge(alpha=self.alpha) for _ in range(n_timepoints)]
            if self.random_weights:
                # Randomly initialize weights and intercepts
                for model in self.models:
                    model.coef_ = np.random.rand(n_sensors, n_features) - 0.5  # Random weights centered around 0
                    model.intercept_ = np.random.rand(n_sensors) - 0.5  # Random intercepts centered around 0
            else:
                for t in range(n_timepoints):
                    Y_t = Y[:, :, t]
                    self.models[t].fit(X, Y_t)

        def predict(self, X):
            n_samples = X.shape[0]
            n_sensors = self.models[0].coef_.shape[0]
            n_timepoints = len(self.models)
            predictions = np.zeros((n_samples, n_sensors, n_timepoints))
            for t, model in enumerate(self.models):
                if self.random_weights:
                    # Use the random weights and intercept to predict; we are missing configurations implicitly achieved when calling .fit()
                    predictions[:, :, t] = X @ model.coef_.T + model.intercept_
                else:
                    predictions[:, :, t] = model.predict(X)
            return predictions    
    


class VisualizationHelper(GLMHelper):
    def __init__(self, subject_id: str = "02"):
        super().__init__(subject_id=subject_id)


    def visualize_GLM_results(self, only_distance: bool = False, separate_plots:bool = False):
        """
        Visualizes results from GLMHelper.predict_from_mapping
        """
        # Load loss dict
        mse_session_losses = self.read_dict_from_json(type_of_content="mse_losses")

        if only_distance:
            # Plot loss as a function of distance of predicted session from "training" session
            fig, ax1 = plt.subplots(figsize=(12, 8))

            # Iterate over each training session
            losses_by_distances = {}
            for train_session, data in mse_session_losses['session_mapping'].items():
                # Calculate distance and collect corresponding losses
                for pred_session, mse in data['session_pred'].items():
                    if train_session != pred_session:
                        distance = abs(int(train_session) - int(pred_session))
                        if distance not in losses_by_distances:
                            losses_by_distances[distance] = {"loss": mse, "num_losses": 1}
                        else:
                            losses_by_distances[distance]["loss"] += mse
                            losses_by_distances[distance]["num_losses"] += 1

            # Calculate average losses over distances
            avg_losses = {}
            num_datapoints = {}
            for distance in range(1,10):
                avg_losses[distance] = losses_by_distances[distance]["loss"] / losses_by_distances[distance]["num_losses"]
                num_datapoints[distance] = losses_by_distances[distance]["num_losses"]

            # Plot
            ax1.plot(avg_losses.keys(), avg_losses.values(), marker='o', linestyle='-', label=f'Average loss')
            ax1.set_xlabel('Distance between "train" and "test" Session')
            ax1.set_ylabel('Mean Squared Error')
            ax1.tick_params(axis='y', labelcolor='b')
            ax1.grid(True)
    
            # Add secondary y-axis for datapoints
            ax2 = ax1.twinx()
            ax2.plot(num_datapoints.keys(), num_datapoints.values(), 'r--', label='Number of datapoints/losses averaged')
            ax2.set_ylabel('Number of Datapoints', color='r')
            ax2.tick_params(axis='y', labelcolor='r')

            # Add a legend with all labels
            lines, labels = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines + lines2, labels + labels2, loc='upper right')
            
            ax1.set_title('MSE vs Distance for Predictions Averaged Across all Sessions')
            plt.grid(True)

            # Save the plot to a file
            plot_folder = f"data_files/visualizations/only_distance/subject_{self.subject_id}"
            plot_file = f"MSE_plot_over_distance.png"
            self.save_plot_as_file(plt=plt, plot_folder=plot_folder, plot_file=plot_file)

        else:
            # Collect self-prediction MSEs for baseline and prepare average non-self-MSE calculation
            self_prediction_mses = {}
            average_prediction_mses = {}
            for session in mse_session_losses['session_mapping']:
                self_prediction_mses[session] = mse_session_losses['session_mapping'][session]['session_pred'][session]
                average_prediction_mses[session] = 0

            # Calculate average MSE for each session from all other training sessions
            for train_session, data in mse_session_losses['session_mapping'].items():
                for pred_session, mse in data['session_pred'].items():
                    if train_session != pred_session:
                        average_prediction_mses[pred_session] += mse
            num_other_sessions = len(self.session_ids_num) - 1
            for session in average_prediction_mses:
                average_prediction_mses[session] /= num_other_sessions

            if separate_plots:
                # Generate separate plots for each training session
                for train_session, data in mse_session_losses['session_mapping'].items():
                    plt.figure(figsize=(10, 6))
                    sessions = list(data['session_pred'].keys())
                    losses = list(data['session_pred'].values())
                    plt.plot(sessions, losses, marker='o', linestyle='-', label=f'Training Session {train_session}')
                    plt.plot(self_prediction_mses.keys(), self_prediction_mses.values(), 'r--', label='Self-prediction MSE')
                    plt.plot(average_prediction_mses.keys(), average_prediction_mses.values(), 'g-.', label='Average Non-self-prediction MSE')

                    plt.title(f'MSE for Predictions from Training Session {train_session}')
                    plt.xlabel('Predicted Session')
                    plt.ylabel('Mean Squared Error')
                    plt.legend()
                    plt.grid(True)

                    # Save the plot to a file
                    plot_folder = f"data_files/visualizations/seperate_plots_{separate_plots}/subject_{self.subject_id}"
                    plot_file = f"MSE_plot_session{train_session}.png"
                    self.save_plot_as_file(plt=plt, plot_folder=plot_folder, plot_file=plot_file)
            else:
                # Generate a single plot with all training sessions
                plt.figure(figsize=(12, 8))
                for train_session, data in mse_session_losses['session_mapping'].items():
                    sessions = list(data['session_pred'].keys())
                    losses = list(data['session_pred'].values())
                    plt.plot(sessions, losses, marker='o', linestyle='-', label=f'Trained on Session {train_session}')
                plt.plot(self_prediction_mses.keys(), self_prediction_mses.values(), 'r--', label='Self-prediction MSE')
                plt.plot(average_prediction_mses.keys(), average_prediction_mses.values(), 'g-.', label='Average Non-self-prediction MSE')
                
                plt.title('MSE for Predictions Across All Sessions')
                plt.xlabel('Prediction Session')
                plt.ylabel('Mean Squared Error')
                plt.legend()
                plt.grid(True)

                # Save the plot to a file
                plot_folder = f"data_files/visualizations/seperate_plots_{separate_plots}/subject_{self.subject_id}"
                plot_file = f"MSE_plot_all_sessions.png"
                self.save_plot_as_file(plt=plt, plot_folder=plot_folder, plot_file=plot_file)
            

