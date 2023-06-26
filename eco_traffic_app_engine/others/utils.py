import glob
import os
import shutil

import pandas as pd


def remove_files(folder_path: str) -> None:
    """
    Remove all the files from a given folder

    :param folder_path: folder where the files will be removed
    :type folder_path: str
    :return: None
    """
    # Iterate over the files
    for filename in os.listdir(folder_path):
        # Get file paths
        file_path = os.path.join(folder_path, filename)
        try:
            # If it is a file unlink it
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            # If it is a directory, remove it
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


def load_dataframe(directory: str) -> pd.DataFrame:
    """
    Load dataframe from all the XLSX files of a given directory

    :param directory: directory where data is stored
    :type directory: str
    :return: dataframe with loaded information
    :rtype: Pandas DataFrame
    """
    df = pd.DataFrame()
    # Iterate over the XLSX files
    for f in glob.glob(directory + "*.xlsx"):
        # Load dataframe
        aux_df = pd.read_excel(f)
        # Append to full dataset
        df = pd.concat([df, aux_df], axis=0)

    return df


# Define a concatenation function
def concat(lists: list) -> list:
    """
    Concat list of lists as a single list

    :param lists: list of lists
    :type lists: list
    :return: concat list
    :rtype: list
    """

    result = []
    for lst in lists:
        result.extend(lst)
    return result
