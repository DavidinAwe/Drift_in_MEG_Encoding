import sys
import os
import importlib.util
import json
import h5py

# Params


# Add AVS directory to sys.path to allow import
avs_project_root_path = "/share/klab/camme/camme/dmasurek/AVS-machine-room-copy/"
sys.path.insert(0, avs_project_root_path)

# Load the required functions
from avs_machine_room.dataloader.load_population_codes.load_h5 import load_pop_code_dynamics

# Read timepoint_dict_crop from json
timepoint_dict_crops_file = open("data_files/timepoint_dict_crops.json")
timepoint_dict_crops_string = timepoint_dict_crops_file.read()
timepoint_dict_crops = json.loads(timepoint_dict_crops_string)

# Load and inspect MEG data
path_to_meg_data = "/share/klab/datasets/avs/population_codes/as02/sensor/filter_0.2_200"
meg_data_file = "as02a_population_codes_fixation_500hz_masked_False.h5"

"""
pop_code_dynamics = load_pop_code_dynamics(subject=["2"], 
                                        session=1,  
                                        input_dir=path_to_meg_data, 
                                        event_type="fixation", 
                                        s_freq=500, 
                                        masked=False, 
                                        take_norm=False
                    )
"""
# Comments to function load_pop_code_dynamics

# docstring says subject should be subject ID as int but function attempts to slice it with [0] and converts it to int --> seems to require list?

# There seems to be a function missing or misquoted in "population_code_tools"/"avs_pop_code_tools": The function "lock_population_code_to_fixation_offset" does not exist in the repository
# AttributeError: module 'avs_machine_room.prepro.source_reconstruction.population_code_tools' has no attribute 'lock_population_code_to_fixation_offset'

#print(f"pop_code_dynamics.keys(): {pop_code_dynamics.keys()}")


# Try it manually

# Iterate over dict, counting timepoints, filling in the data for each timepoint
def insert_meg_into_crop_dict(timepoint_dict_crops: dict, meg_data: dict, num_epochs: int):
    total_index = 0
    for session_id in timepoint_dict_crops["sessions"].keys():
        print(f"Filling in meg data for session {session_id}")
        for trial_id in timepoint_dict_crops["sessions"][session_id]["trials"].keys():
            for timepoint_id in timepoint_dict_crops["sessions"][session_id]["trials"][trial_id]["timepoints"].keys():
                # Stop if meg data from file is completely extracted
                if total_index >= num_epochs:
                    return timepoint_dict_crops

                # Debugging
                #print(f"session_id: {session_id}, trial_id: {trial_id}, timepoint_id: {timepoint_id}")

                # Fill in meg data for timepoint (convert numpy array to list for json serialization)
                # grad
                timepoint_dict_crops["sessions"][session_id]["trials"][trial_id]["timepoints"][timepoint_id]["meg"]["grad"] = meg_data["grad"][total_index][:][:]  #.tolist()
                # meg
                timepoint_dict_crops["sessions"][session_id]["trials"][trial_id]["timepoints"][timepoint_id]["meg"]["mag"] = meg_data["mag"][total_index][:][:]  #.tolist()

                total_index += 1

# Define globals
meg_data = {}
num_epochs = None
meg_crops_by_timepoints = {}

# Read .h5 file
with h5py.File(os.path.join(path_to_meg_data, meg_data_file), "r") as f:
    # Print meg file info
    print(f.attrs.keys())
    print(f"f.attrs['random_epochs']: {f.attrs['random_epochs']}")
    print(f"f.attrs['rois']: {f.attrs['rois']}")
    print(f"f.attrs['session']: {f.attrs['session']}")
    print(f"f.attrs['subject']: {f.attrs['subject']}")

    print(f"f.keys(): {f.keys()}")
    print(f"f['grad']['onset'].shape: {f['grad']['onset'].shape}") # participant 2, session a: (2874, 204, 601)
    print(f"f['mag']['onset'].shape: {f['mag']['onset'].shape}") # participant 2, session a: (2874, 102, 601)

    print(f"num timepoints: {len(f.attrs['times'])}")

    # session 1 trial 1 starts at 5350
    # we have 2875 (2874 starting from 0) epochs in session a, those belong to 2874 different crops/time_in_trials
    # so I have to go through the dict in the order of creation to map crops to meg epochs?

    meg_data["grad"] = f['grad']['onset']  #(2874, 204, 601)
    meg_data["mag"] = f['mag']['onset']  #(2874, 102, 601)
    num_epochs = f['grad']['onset'].shape[0]

    print(f"num_epochs: {num_epochs}")

    #combined_meg = np.concatenate([meg_data["grad"], meg_data["mag"]], axis=1) #(2874, 306, 601)

    #meg_crops_by_timepoints = insert_meg_into_crop_dict(timepoint_dict_crops, meg_data, num_epochs)


print("Done filling meg data in dict.")

# No export yet, datatype to be debated

print("Done exporting meg data.")




