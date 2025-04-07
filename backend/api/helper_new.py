# -*- coding: utf-8 -*-
"""
Created on Tue Mar 22 11:48:05 2022

@author: ABhishankar Kumar, Karthikeyan
"""
import os
import math
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pandas.api.types import is_numeric_dtype
from scipy.spatial.distance import jensenshannon as js
from scipy.stats import median_abs_deviation as mad
import plotly.graph_objects as go
from database import insert_data_to_mysql
import plotly.express as px


foundry="Munjal Line 1"

basepath = os.getcwd()
datapath = os.path.join(os.path.join(basepath,"Data"),foundry)
jsonpath=os.path.join(os.path.join(basepath,"Configfile"),foundry)
results_dir = os.path.join(os.path.join(basepath,"results"),foundry)

def date_time_converter(df, col_name):
    """

    It convert date into date time format
    param:
        df: DataFrame containing date time format
        col_name: Column name of date time
    return:
        df: DataFrame containing col_name in date time format

    """
    if not issubclass(type(df), pd.DataFrame):
        raise TypeError("df should be a Pandas DataFrame")
    if not issubclass(type(col_name), str):
        raise TypeError("col_name should be a string")
    if col_name not in df.columns:
        raise KeyError(f' {col_name} is not present in the dataframe')

    df[col_name] = pd.to_datetime(df[col_name])
    return df

def align_data(prepared_sand_data, rejection_data, config_file, analysis_frequency):
    """
    It align prepared sand and rejection data based on analysis frequency

    param:
        prepared_sand: sand properties data
        dtype: Pandas dataframe
        rejection_data: Rejection data
        dtype: Pandas dataframe
        analysis_frequency: frequency of analysis
    return
        aligned data
        dtype: Pandas dataframe

    """
    analysis_frequency = analysis_frequency

    if not issubclass(type(prepared_sand_data), pd.DataFrame):
        raise TypeError("prepared_sand_data should be a Pandas DataFrame")
    if not issubclass(type(rejection_data), pd.DataFrame):
        raise TypeError("rejection_data should be a Pandas DataFrame")

    if not issubclass(type(analysis_frequency), list):
        raise TypeError("analysis_frequency should be a list")

    if not issubclass(type(config_file), dict):
        raise TypeError("config_file should be a dict")

    defect_keys = list(
        config_file["Defectwise sand properties based on fishbone"].keys())

    defect_type = config_file["defect_for_analysis"]
    

    if defect_type not in defect_keys:
        raise KeyError(
            f' {defect_type} is not present in the configuration files')

    rejection_data['Date'] = rejection_data['Production_Date'].dt.date
    

    rej_for_analysis = config_file["defect_mapping"][defect_type]

    rejection_field = defect_type + " "+"%"

  

    # rejection_data = rejection_data.groupby(analysis_frequency).sum().reset_index()
    numeric_cols = rejection_data.select_dtypes(include=[np.number]).columns.tolist()
    rejection_data = rejection_data.groupby(analysis_frequency)[numeric_cols].sum().reset_index()

    
    config_file["total_produced_qty"] = "Total_Quantity_Produced__no"
    # rejection_data[rejection_field]=100*(rejection_data[rej_for_analysis].sum(axis=5))/rejection_data['Total Quantity Produced (no)']
    try:
        rejection_data[rejection_field] = 100*(rejection_data[rej_for_analysis].sum(axis=1))/rejection_data[config_file["total_produced_qty"]]
    except KeyError:
        raise KeyError(
            f' {config_file["total_produced_qty"]} is not in columns')
    required_rejection_col = analysis_frequency+[rejection_field]

    rejection_data = rejection_data[required_rejection_col]
    prepared_sand_data['Date'] = prepared_sand_data['Date'].dt.date
    

    prepared_sand_data = prepared_sand_data.drop(columns=["Component_Id", "Heat_No"], errors='ignore')
 

    # prepared_sand_data = prepared_sand_data.groupby(analysis_frequency).mean().reset_index()
    grouped = prepared_sand_data.groupby(analysis_frequency)

    numeric_cols = prepared_sand_data.select_dtypes(include=[np.number]).columns.tolist()
    prepared_sand_data_mean = grouped[numeric_cols].mean().reset_index()

    prepared_sand_data = prepared_sand_data_mean



    fishbone_prepared_sand = config_file["Defectwise sand properties based on fishbone"][defect_type]
    available_features = list(set(fishbone_prepared_sand) & set(
        list(prepared_sand_data.columns)))
    required_prep_sand = analysis_frequency + available_features  # +fishbone_prepared_sand

    numeric_cols = prepared_sand_data.select_dtypes(include=[np.number]).columns
    prepared_sand_data[numeric_cols] = prepared_sand_data[numeric_cols].fillna(prepared_sand_data[numeric_cols].mean())

    prepared_sand_data = prepared_sand_data[required_prep_sand]

    prep_sand_rej = pd.merge(prepared_sand_data, rejection_data, on=analysis_frequency, how='inner')
    prep_sand_rej.index = range(len(prep_sand_rej))

    # print(prep_sand_rej)

    return prep_sand_rej


def bin_optimizer(df, col):
    """
    Function to calculate optimal no. of bins with proper error handling

    Parameters
    ----------
    df : Prepared sand data
        TYPE: Pandas Dataframe
    col : Column for analysis
        TYPE: str

    Returns: optimal no. of bin
        TYPE: int
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df should be a pandas DataFrame")
    if not isinstance(col, str):
        raise TypeError("col should be a string")
        
    # Check if column has valid numeric data
    valid_data = df[col].dropna()
    if len(valid_data) == 0:
        return 30  
        
    q1 = np.nanpercentile(valid_data, 25)
    q3 = np.nanpercentile(valid_data, 75)
    len_df = len(valid_data)
    
    if q1 == q3:
        return 30
        
    bin_width = (2*(q3 - q1))/(len_df**(1/3))
    
    if bin_width == 0 or np.isnan(bin_width):
        return 30
        
    data_range = valid_data.max() - valid_data.min()
    if data_range == 0:
        return 30
        
    bins = np.ceil(data_range / bin_width)
    
    # Final safety check
    if np.isnan(bins):
        return 30
        
    return int(bins)

def get_data_for_analysis(prepared_sand_data, rejection_data, config_file, analysis_frequency):
    """
    It get aligned prepared sand and rejection data based on user defined date

    Parameters
    ----------
    prepared_sand_data : Prepared sand data for analysis. It should contain reference data and comparision data
        TYPE: Pandas Dataframe

    rejection_data : Rejection data for analysis. It should contain reference data and comparision data
        TYPE: Pandas Dataframe
    config_file : configuration files for the analysis
        TYPE: JSON
    Returns: Dictionary  containing reference and comparision data
        TYPE: Pandas Dataframe
    -------

    """
    data_for_analysis = {}
    prep_sand_rej = align_data(prepared_sand_data, rejection_data, config_file, analysis_frequency)
    if prep_sand_rej.shape[0] < config_file["data_sufficiency_check"]["main_data"]:
        raise RuntimeError("Data is not sufficient for statistical analysis")

    prep_sand_rej['Date'] = pd.to_datetime(prep_sand_rej['Date'])

    cols_for_bins = list(set(prep_sand_rej.columns) &
                         set(prepared_sand_data.columns))

    bin_dict = {}
    for col in cols_for_bins:
        if is_numeric_dtype(prep_sand_rej[col]):
            try:
                # Check if column has valid data for binning
                valid_data = prep_sand_rej[col].dropna()
                if len(valid_data) > 0 and valid_data.nunique() > 1:
                    opt_bin = bin_optimizer(prep_sand_rej, col)
                    # Calculate bin edges manually to ensure they're valid
                    min_val = valid_data.min()
                    max_val = valid_data.max()
                    if min_val != max_val:
                        bin_edges = np.linspace(min_val, max_val, opt_bin + 1)
                        prep_sand_rej[f"{col}_bins"] = pd.cut(
                            prep_sand_rej[col], 
                            bins=bin_edges, 
                            right=False,
                            duplicates='drop'
                        )
                        bin_dict[col] = opt_bin
            except Exception as e:
                # If binning fails for any reason, skip this column
                print(f"Warning: Could not create bins for column {col}: {str(e)}")
                continue

    mask_ref = (prep_sand_rej['Date'].astype(str) >= config_file["data_selection"]["reference_period"][0]) & (
        prep_sand_rej['Date'].astype(str) <= config_file["data_selection"]["reference_period"][1])
    mask_compar = (prep_sand_rej['Date'].astype(str) >= config_file["data_selection"]["comparison_period"][0]) & (
        prep_sand_rej['Date'].astype(str) <= config_file["data_selection"]["comparison_period"][1])
    
    
    ref_data = prep_sand_rej[mask_ref]
    ref_data['Date'] = ref_data['Date'].dt.date

    ref_data.index = range(len(ref_data))

    comp_data = prep_sand_rej[mask_compar]
    comp_data['Date'] = comp_data['Date'].dt.date
    comp_data.index = range(len(comp_data))
    data_for_analysis['ref_data'] = ref_data
    data_for_analysis['comp_data'] = comp_data
    # insert_data_to_mysql(data_for_analysis['ref_data'], foundry, config_file['defect_for_analysis'],"ref_data" )
    # insert_data_to_mysql(data_for_analysis['comp_data'], foundry, config_file['defect_for_analysis'],"comp_data")
    data_for_analysis['ref_data'].to_excel(os.path.join(results_dir, 'data_for_analysisref.xlsx'),index=False)
    data_for_analysis['comp_data'].to_excel(os.path.join(results_dir, 'data_for_analysiscomp.xlsx'),index=False)
    return data_for_analysis, bin_dict



def dist_plot(data_for_analysis, config_file, analysis_frequency,results_dir, show_plot=True):
    """
    It create distribution plot


    Parameters
    ----------
    data_for_analysis : It is a dictionary containing reference data and comparision data
        TYPE: Dictionary
    config_file : Configuration file
        TYPE: JSON

    Returns: distribution plot, data for distribution plot, plot labels
        TYPE: dict, list
    -------

    """
    master_key = ['ref_data', 'comp_data']
    if not issubclass(type(data_for_analysis), dict):
        raise TypeError("data_for_analysis should be a dictionary")
    missing_key = list(set(master_key)-set(list(data_for_analysis.keys())))

    if set(master_key).issubset(data_for_analysis) == False:
        raise KeyError(
            f' {missing_key} is not present in the data_for_analysis')

    if not issubclass(type(analysis_frequency), list):
        raise TypeError("analysis_frequency should be a list")

    ref_data = data_for_analysis['ref_data']
    comp_data = data_for_analysis['comp_data']

    legend_ref = str(ref_data['Date'].iloc[0]) + " " + \
        'to' " " + str(ref_data['Date'].iloc[-1])
    legend_comp = str(comp_data['Date'].iloc[0]) + \
        " " + 'to'+" " + str(comp_data['Date'].iloc[-1])

    feature_to_drop = analysis_frequency + \
        [config_file["defect_for_analysis"]+" "+"%"]
    # ref_data = ref_data.drop(feature_to_drop, axis=1)
    # Ensure the column exists before dropping
    feature_to_drop = [col for col in feature_to_drop if col in ref_data.columns]
    if feature_to_drop:  
        ref_data = ref_data.drop(feature_to_drop, axis=1)

    comp_data = comp_data.drop(feature_to_drop, axis=1)

    dist_dict = {}
    plot_data = {}
    plot_labels = [legend_ref, legend_comp]
    div_data_dict = {}
    div_dict = {}
    mad_dict = {}

    col_bins = [x for x in ref_data.columns if "bins" in x]

    for bin_col in col_bins:
        ref_df = pd.DataFrame(
            pd.Series(ref_data[bin_col].value_counts(normalize=True)))
        comp_df = pd.DataFrame(
            pd.Series(comp_data[bin_col].value_counts(normalize=True)))
        binning_df = pd.merge(ref_df.reset_index(), comp_df.reset_index(), how="left",
                              on="index").sort_values(by="index")
        x_col = bin_col + "_x"
        y_col = bin_col + "_y"
        binning_df[[x_col, y_col]].fillna(0, inplace=True)
        div_data_dict[bin_col] = binning_df

        js_score = js(binning_df[x_col], binning_df[y_col])
        div_dict[bin_col] = np.round(js_score, 2)

        del binning_df, js_score

    for col in ref_data.columns:
        if is_numeric_dtype(ref_data[col]):
            dist_dict[col] = {}
            dist_dict[col]["ref_data"] = ref_data[col]
            dist_dict[col]["comp_data"] = comp_data[col]
            plot_data[col] = {}
            plt.figure(figsize =(config_file["figure_configuration"]["dist_plot"]["figsize"][0],config_file["figure_configuration"]["dist_plot"]["figsize"][1]))
            fig1 = sns.kdeplot(ref_data[col], shade=True)
            # ref_x, ref_y = fig1.lines[0].get_data()
            plot_data[col]["ref_data"] = {}
            # plot_data[col]["ref_data"]["x"] = ref_x
            # plot_data[col]["ref_data"]["y"] = ref_y
            fig2 = sns.kdeplot(comp_data[col], shade=True)
            # comp_x, comp_y = fig2.lines[1].get_data()
            plot_data[col]["comp_data"] = {}            # plot_data[col]["comp_data"]["x"] = comp_x
            # plot_data[col]["comp_data"]["y"] = comp_y
            if show_plot:
                plt.legend(loc=config_file["figure_configuration"]["dist_plot"]["legend_location"],labels=["Reference Period","Comparison Period"])
                plt.xlabel(col,fontsize = config_file["figure_configuration"]["dist_plot"]["fontsize"])
                plt.ylabel('Density',fontsize = config_file["figure_configuration"]["dist_plot"]["fontsize"] )
                # title="Distribution plot of" + " "+ col + "with divergence: "+ str(np.round(div_dict[f"{col}_bins"],2))
                title="Distribution plot of" + " "+ col
                plt.title(title, fontsize=config_file["figure_configuration"]["dist_plot"]["title_fontsize"])  
                if "/" in col:
                    col = col.replace("/","_")
                plt.savefig(os.path.join(results_dir, f"Distribution plot of {col}.jpeg"), dpi=1000)
                plt.show()

    return dist_dict, plot_data, plot_labels, div_data_dict, div_dict
    

def box_plot(data_for_analysis, config_file, analysis_frequency, results_dir,show_plot=True):
    """
    It create box plot for analysis period and compute absolute deviation from median

    Parameters
    ----------
    data_for_analysis : it contains both period data
        TYPE: dictionary
    config_file : Configuration file
        TYPE

    Returns: box plot, data for box plot, dict for absolute changes
        TYPE: dict
    -------

    """

    master_key = ['ref_data', 'comp_data']
    if not issubclass(type(data_for_analysis), dict):
        raise TypeError("data_for_analysis should be a dictionary")
    missing_key = list(set(master_key)-set(list(data_for_analysis.keys())))

    if set(master_key).issubset(data_for_analysis) == False:
        raise KeyError(
            f' {missing_key} is not present in the data_for_analysis')

    if not issubclass(type(analysis_frequency), list):
        raise TypeError("analysis_frequency should be a list")

    ref_data = data_for_analysis['ref_data']
    comp_data = data_for_analysis['comp_data']

    legend_ref = str(ref_data['Date'].iloc[0]) + " " + \
        'to' " " + str(ref_data['Date'].iloc[-1])
    legend_comp = str(comp_data['Date'].iloc[0]) + \
        " " + 'to'+" " + str(comp_data['Date'].iloc[-1])

    feature_to_drop = analysis_frequency + \
        [config_file["defect_for_analysis"]+" "+"%"]


    feature_to_drop = [col for col in feature_to_drop if col in ref_data.columns]
    if feature_to_drop:  
        ref_data = ref_data.drop(feature_to_drop, axis=1)

    # comp_data = comp_data.drop(feature_to_drop, axis=1)
    # Ensure columns exist before dropping
    feature_to_drop = [col for col in feature_to_drop if col in comp_data.columns]
    if feature_to_drop:
        comp_data = comp_data.drop(feature_to_drop, axis=1)


    # ref_data = ref_data.drop(feature_to_drop, axis=1)
    # comp_data = comp_data.drop(feature_to_drop, axis=1)

    summary_dict = {}
    box_dict = {}

    for col in ref_data.columns:
        if is_numeric_dtype(ref_data[col]):
            data1 = ref_data[col].to_frame()
            data1.index = range(len(data1))
            data1['Date'] = legend_ref

            data2 = comp_data[col].to_frame()
            data2.index = range(len(data2))
            data2['Date'] = legend_comp

            dfnew = pd.concat([data1, data2], axis=0)
            box_dict[col] = dfnew

            change = 100*(data1[col].median()-data2[col].median())/data1[col].median()
            summary_dict[col] = round(abs(change), 2)

            if show_plot:
                fig = plt.figure(figsize=(config_file["figure_configuration"]["dist_plot"]["figsize"]
                                 [0], config_file["figure_configuration"]["dist_plot"]["figsize"][1]))
                title = 'Absolute change in' + " " + col + \
                    ":" + str(round(abs(change), 2)) + " " + "%"
                # .set(title=title,fontsize=20)###sns.boxplot(df1[item],color="r")
                fig = sns.boxplot(x='Date', y=col, data=dfnew)
                fig.set_xlabel(
                    'Period', fontsize=config_file["figure_configuration"]["dist_plot"]["fontsize"])
                fig.set_ylabel(
                    col, fontsize=config_file["figure_configuration"]["box_plot"]["fontsize"])

                plt.title(
                    title, fontsize=config_file["figure_configuration"]["box_plot"]["title_fontsize"])
                fig.set_xticklabels(fig.get_xticklabels(), rotation=45, horizontalalignment='right',
                                    fontsize=config_file["figure_configuration"]["dist_plot"]["fontsize"])
                # if "/" in col:
                #     col = col.replace("/", "_")
                # plt.savefig(os.path.join(results_dir, f"Box plot of {col}.jpeg"), dpi=1000, bbox_inches="tight")
                
                if "/" in col:
                    col = col.replace("/", "_")
                save_path = os.path.join(results_dir, f"Box plot of {col}.jpeg")
                plt.savefig(save_path, dpi=1000, bbox_inches="tight")
                # print(f"Plot saved successfully at: {save_path}")
                plt.show()
                plt.close()

    return box_dict, summary_dict


def correlation_plot(data_for_analysis, config_file, analysis_frequency,results_dir, show_plot=True):
    """


    Parameters
    ----------
    data_for_analysis : TYPE
        DESCRIPTION.
    config_file : TYPE
        DESCRIPTION.

    Returns: correlation plot, data for correlation plot, plot labels
        TYPE: dict, list
    -------

    
    """
    master_key = ['ref_data', 'comp_data']
    if not issubclass(type(data_for_analysis), dict):
        raise TypeError("data_for_analysis should be a dictionary")
    missing_key = list(set(master_key)-set(list(data_for_analysis.keys())))

    if set(master_key).issubset(data_for_analysis) == False:
        raise KeyError(
            f' {missing_key} is not present in the data_for_analysis')

    if not issubclass(type(analysis_frequency), list):
        raise TypeError("analysis_frequency should be a list")

    ref_data = data_for_analysis['ref_data']
    comp_data = data_for_analysis['comp_data']

    legend_ref = str(ref_data['Date'].iloc[0]) + " " + \
        'to' " " + str(ref_data['Date'].iloc[-1])
    legend_comp = str(comp_data['Date'].iloc[0]) + \
        " " + 'to'+" " + str(comp_data['Date'].iloc[-1])

    feature_to_drop = analysis_frequency
    defect_type = config_file["defect_for_analysis"]
    rejection_field = defect_type + " "+"%"
    # ref_data = ref_data.drop(feature_to_drop, axis=1)

    feature_to_drop = [col for col in feature_to_drop if col in ref_data.columns]
    if feature_to_drop:  
        ref_data = ref_data.drop(feature_to_drop, axis=1)

    # comp_data = comp_data.drop(feature_to_drop, axis=1)
    # Ensure columns exist before dropping
    feature_to_drop = [col for col in feature_to_drop if col in comp_data.columns]
    if feature_to_drop:
        comp_data = comp_data.drop(feature_to_drop, axis=1)

    # comp_data = comp_data.drop(feature_to_drop, axis=1)

    corr_dict = {}
    plot_labels = [legend_ref, legend_comp]
    color_palette = {
        legend_ref: 'r',
        legend_comp: 'b'
    }
    for col in ref_data.columns:
        if is_numeric_dtype(ref_data[col]):
            if col not in [rejection_field]:
                data1 = ref_data[[col, rejection_field]].copy()
                data2 = comp_data[[col, rejection_field]].copy()
                
                
                data1['Period'] = legend_ref
                data2['Period'] = legend_comp
                
             
                plot_data = pd.concat([data1, data2], ignore_index=True)
                
                corr_dict[col] = {}
                corr_dict[col]["data1"] = data1
                corr_dict[col]["data2"] = data2
                
                if show_plot:
                    plt.figure(figsize=(config_file["figure_configuration"]["dist_plot"]["figsize"][0],
                                      config_file["figure_configuration"]["dist_plot"]["figsize"][1]))
                    
                    
                    sns.scatterplot(data=plot_data, 
                                  x=col,
                                  y=rejection_field, 
                                  hue='Period',
                                  palette=color_palette)
                    
                    plt.xlabel(col, fontsize=config_file["figure_configuration"]["correlation_plot"]["fontsize"])
                    plt.ylabel(rejection_field, fontsize=config_file["figure_configuration"]["correlation_plot"]["fontsize"])
                    
                    title = rejection_field + " " + 'vs' + " " + col
                    plt.title(title, fontsize=config_file["figure_configuration"]["correlation_plot"]["title_fontsize"])
                    plt.ylim(0,)
                    
                    
                    safe_col = col.replace("/", "_") if "/" in col else col
                    
                   
                    plt.savefig(os.path.join(results_dir, f"Correlation plot of {safe_col}.jpeg"), 
                              dpi=1000, 
                              bbox_inches='tight')
                    plt.show()
                    plt.close()  
    
    return corr_dict, plot_labels


def whisker_calc(data):
    """
    Function to calculate lower and upper whisker

    Parameters
    ----------
    data : pandas.Series
        Data for calculation of lower and upper whisker

    Returns: lower whisker and upper whisker values
        TYPE: float, float
    """
    if not isinstance(data, pd.Series):
        raise TypeError("data must be a pandas.Series")
    q1 = np.nanpercentile(data, 25)
    q3 = np.nanpercentile(data, 75)
    iqr = q3 - q1
    lower_whisker = q1 - 1.5*iqr
    upper_whisker = q3 + 1.5*iqr
    return lower_whisker, upper_whisker



def outlier_calc(box_dict):
    """
    Function to find the outlier value for all the properties for
    reference and comparison data

    Parameters
    ----------
    box_dict : dict
        Dictionary containing all the properties and their
        reference and comparison dataframe

    Returns: outlier value dictionary
        TYPE: dict
    """
    if not isinstance(box_dict, dict):
        raise TypeError("box_dict must be a python dictionary")

    outlier_dict = {}
    cols = list(box_dict.keys())

    for col in cols:
        outlier_dict[col] = {}
        temp_df = box_dict[col]

        unique_dates = temp_df["Date"].unique()
        if len(unique_dates) < 2:
            print(f"Warning: Not enough unique dates for comparison in {col}. Skipping.")
            continue  

        ref_date = unique_dates[0]
        comp_date = unique_dates[1]

        ref_df = temp_df[temp_df["Date"] == ref_date]
        comp_df = temp_df[temp_df["Date"] == comp_date]

        lower_whisker_ref, upper_whisker_ref = whisker_calc(ref_df[col])
        lower_whisker_comp, upper_whisker_comp = whisker_calc(comp_df[col])

        outlier_dict[col][ref_date] = [lower_whisker_ref, upper_whisker_ref]
        outlier_dict[col][comp_date] = [lower_whisker_comp, upper_whisker_comp]

    return outlier_dict


def find_outliers(outlier_dict, box_dict):
    """
    Function to find the outliers for all the properties for
    reference and comparison data.

    Parameters
    ----------
    box_dict : dict
        Dictionary containing all the properties and their
        reference and comparison dataframe.
    outlier_dict : dict
        Dictionary containing all the properties and their
        reference and comparison outlier values.

    Returns:
        outliers dictionary
        TYPE: dict
    """
    if not isinstance(box_dict, dict):
        raise TypeError("box_dict must be a python dictionary")
    if not isinstance(outlier_dict, dict):
        raise TypeError("outlier_dict must be a python dictionary")

    outliers = {}
    cols = list(box_dict.keys())

    for col in cols:
        outliers[col] = {}
        temp_df = box_dict[col]

        unique_dates = temp_df["Date"].unique()
        
        # Ensure we have at least two unique dates
        if len(unique_dates) < 2:
            print(f"Warning: Not enough unique dates for comparison in {col}. Skipping.")
            continue  # Skip processing if there's only one unique date

        ref_date = unique_dates[0]
        comp_date = unique_dates[1]

        ref_df = temp_df[temp_df["Date"] == ref_date]
        comp_df = temp_df[temp_df["Date"] == comp_date]

        outlier = outlier_dict.get(col, {})

        try:
            ref_outliers = list(ref_df[
                (ref_df[col] < outlier.get(ref_date, [None, None])[0]) | 
                (ref_df[col] > outlier.get(ref_date, [None, None])[1])
            ][col].values.round(2))

            comp_outliers = list(comp_df[
                (comp_df[col] < outlier.get(comp_date, [None, None])[0]) | 
                (comp_df[col] > outlier.get(comp_date, [None, None])[1])
            ][col].values.round(2))
        except:
            ref_outliers = []
            comp_outliers = []

        outliers[col][ref_date] = ref_outliers
        outliers[col][comp_date] = comp_outliers

    return outliers


def product_mix_calculator(rej_data, config_file, grouping_info):
    if not isinstance(rej_data, pd.DataFrame):
        raise TypeError("rej_data must be a pandas DataFrame")
    if not isinstance(config_file, dict):
        raise TypeError("config_file must be a python dictionary")

    rej_data = rej_data.rename(columns={"Production Date": "Date"})
    rej_data['Date'] = pd.to_datetime(rej_data['Date'])
    rej_data["prodn_wt"] = rej_data[config_file["total_produced_qty"]] * rej_data["Nett Casting Wt (Kg)"]

    if config_file["group_wise_analysis"]:
        agg_var = "group"
        for key in list(grouping_info.keys()):
            if key.lower() != "group_all":
                rej_data.loc[rej_data["Component Id"].astype(str).isin(grouping_info[key]), agg_var] = key
    elif config_file["component_wise_analysis"]:
        agg_var = "comp"
        selected_components = config_file["component_for_analysis"]
        if not isinstance(selected_components, list):
            selected_components = [selected_components]  
        
        rej_data = rej_data[rej_data["Component Id"].isin(selected_components)]
        rej_data[agg_var] = rej_data["Component Id"].astype(str)
    else:
        agg_var = "Component Id"

    rej_data = rej_data[["Date", agg_var, "prodn_wt"]]

   
    mask_ref = (rej_data['Date'] >= config_file["data_selection"]["reference_period"][0]) & (
        rej_data['Date'] <= config_file["data_selection"]["reference_period"][1])
    mask_compar = (rej_data['Date'] >= config_file["data_selection"]["comparison_period"][0]) & (
        rej_data['Date'] <= config_file["data_selection"]["comparison_period"][1])

    ref_data = rej_data[mask_ref].copy()
    comp_data = rej_data[mask_compar].copy()

    ref_data['Date'] = ref_data['Date'].dt.date
    comp_data['Date'] = comp_data['Date'].dt.date

    ref_data.index = range(len(ref_data))
    comp_data.index = range(len(comp_data))

    prod_mix_dict = {}

    
    agg_ref = ref_data.groupby(agg_var, as_index=False)["prodn_wt"].sum()
    agg_comp = comp_data.groupby(agg_var, as_index=False)["prodn_wt"].sum()

    for item in agg_ref[agg_var].unique():
        ref_value = agg_ref[agg_ref[agg_var] == item]["prodn_wt"].values[0] if item in agg_ref[agg_var].values else 0
        comp_value = agg_comp[agg_comp[agg_var] == item]["prodn_wt"].values[0] if item in agg_comp[agg_var].values else 0

        if ref_value > 0:
            change_percentage = round((comp_value - ref_value) / ref_value * 100, 2)
        else:
            change_percentage = 0.0015

        prod_mix_dict[str(item)] = change_percentage

    return prod_mix_dict
