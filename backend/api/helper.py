# -*- coding: utf-8 -*-
"""
Created on Tue Mar 22 11:48:05 2022

@author: ABhishankar Kumar, Karthikeyan
"""
import os
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pandas.api.types import is_numeric_dtype
from scipy.spatial.distance import jensenshannon as js
from scipy.stats import median_abs_deviation as mad

sns.set_style("whitegrid")

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

    rejection_data['date'] = rejection_data['date'].dt.date

    rej_for_analysis = config_file["defect_mapping"][defect_type]

    rejection_field = defect_type + " "+"%"


    rejection_data = rejection_data.groupby(analysis_frequency).sum().reset_index()

    # rejection_data[rejection_field]=100*(rejection_data[rej_for_analysis].sum(axis=1))/rejection_data['total_quantity_produced']
    try:
        rejection_data[rejection_field] = 100*(rejection_data[rej_for_analysis].sum(
            axis=1))/rejection_data[config_file["total_produced_qty"]]
    except KeyError:
        raise KeyError(
            f' {config_file["total_produced_qty"]} is not in columns')
    required_rejection_col = analysis_frequency+[rejection_field]

    rejection_data = rejection_data[required_rejection_col]
    prepared_sand_data['date'] = prepared_sand_data['date'].dt.date

    prepared_sand_data = prepared_sand_data.groupby(
        analysis_frequency).mean().reset_index()

    fishbone_prepared_sand = config_file["Defectwise sand properties based on fishbone"][defect_type]
    available_features = list(set(fishbone_prepared_sand) & set(
        list(prepared_sand_data.columns)))
    required_prep_sand = analysis_frequency + \
        available_features  # +fishbone_prepared_sand

    prepared_sand_data = prepared_sand_data.fillna(prepared_sand_data.mean())
    prepared_sand_data = prepared_sand_data[required_prep_sand]

    prep_sand_rej = pd.merge(
        prepared_sand_data, rejection_data, on=analysis_frequency, how='inner')
    prep_sand_rej.index = range(len(prep_sand_rej))
    return prep_sand_rej


def bin_optimizer(df, col):
    """
    Function to calculate optimal no. of bins

    Parameters
    ----------
    df : Prepared sansd data
        TYPE: Pandas Dataframe
    col : Column for analsysis
        TYPE: Pandas Dataframe

    Returns: optimal no. of bin
        TYPE: int

    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df should be a pandas DataFrame")
    if not isinstance(col, str):
        raise TypeError("col should be a string")

    q1 = np.nanpercentile(df[col], 25)
    q3 = np.nanpercentile(df[col], 75)
    len_df = len(df)

    bin_width = (2*(q3 - q1))/(len_df**(1/3))
    if np.round(bin_width, 2) != 0.00:
        bins = np.ceil((df[col].max() - df[col].min()) / bin_width)
        return int(bins)
    else:
        return 30


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

    prep_sand_rej['date'] = pd.to_datetime(prep_sand_rej['date'])

    cols_for_bins = list(set(prep_sand_rej.columns) &
                         set(prepared_sand_data.columns))

    bin_dict = {}
    for col in cols_for_bins:
        if is_numeric_dtype(prep_sand_rej[col]):
            if prep_sand_rej[col].dropna().empty:
                continue
            opt_bin = bin_optimizer(prep_sand_rej, col)
            prep_sand_rej[f"{col}_bins"] = pd.cut(
                prep_sand_rej[col], bins=opt_bin, right=False)
            bin_dict[col] = opt_bin
            del opt_bin

    mask_ref = (prep_sand_rej['date'].astype(str) >= config_file["data_selection"]["reference_period"][0]) & (
        prep_sand_rej['date'].astype(str) <= config_file["data_selection"]["reference_period"][1])
    mask_compar = (prep_sand_rej['date'].astype(str) >= config_file["data_selection"]["comparison_period"][0]) & (
        prep_sand_rej['date'].astype(str) <= config_file["data_selection"]["comparison_period"][1])
    ref_data = prep_sand_rej[mask_ref]
    ref_data['date'] = ref_data['date'].dt.date

    ref_data.index = range(len(ref_data))

    comp_data = prep_sand_rej[mask_compar]
    comp_data['date'] = comp_data['date'].dt.date
    comp_data.index = range(len(comp_data))
    data_for_analysis['ref_data'] = ref_data
    data_for_analysis['comp_data'] = comp_data
    return data_for_analysis, bin_dict


def dist_plot(data_for_analysis, config_file, analysis_frequency, show_plot=False,results_dir=None):
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

    legend_ref = str(ref_data['date'].iloc[0]) + " " + \
        'to' " " + str(ref_data['date'].iloc[-1])
    legend_comp = str(comp_data['date'].iloc[0]) + \
        " " + 'to'+" " + str(comp_data['date'].iloc[-1])

    feature_to_drop = analysis_frequency + \
        [config_file["defect_for_analysis"]+" "+"%"]
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
            try:
                dist_dict[col] = {}
                dist_dict[col]["ref_data"] = ref_data[col]
                dist_dict[col]["comp_data"] = comp_data[col]
                if (ref_data[col].std() > 0.01) & (comp_data[col].std() > 0.01):
                    #mad_dict[col] = np.round((100*(mad(comp_data[col]) - mad(ref_data[col]))/mad(ref_data[col])),2)
                    mad_dict[col] = np.round((mad(comp_data[col])/mad(ref_data[col])),2)
                else:
                    mad_dict[col] = np.nan
                plot_data[col] = {}
                plt.figure(figsize=(config_file["figure_configuration"]["dist_plot"]["figsize"]
                        [0], config_file["figure_configuration"]["dist_plot"]["figsize"][1]))
            
                fig1 = sns.kdeplot(ref_data[col], shade=False)
                ref_x, ref_y = fig1.lines[0].get_data()
                plot_data[col]["ref_data"] = {}
                plot_data[col]["ref_data"]["x"] = ref_x
                plot_data[col]["ref_data"]["y"] = ref_y
                fig2 = sns.kdeplot(comp_data[col], shade=False)
                comp_x, comp_y = fig2.lines[1].get_data()
                plot_data[col]["comp_data"] = {}
                plot_data[col]["comp_data"]["x"] = comp_x
                plot_data[col]["comp_data"]["y"] = comp_y
            except:
                continue
            if show_plot:
                plt.legend(loc=config_file["figure_configuration"]["dist_plot"]["legend_location"], labels=[
                           legend_ref, legend_comp])
                plt.xlabel(
                    col, fontsize=config_file["figure_configuration"]["dist_plot"]["fontsize"])
                plt.ylabel(
                    'Density', fontsize=config_file["figure_configuration"]["dist_plot"]["fontsize"])
                title = "Distribution plot of" + " " + col 
                plt.title(
                    title, fontsize=config_file["figure_configuration"]["dist_plot"]["title_fontsize"])
                if "/" in col:
                    col = col.replace("/", "_")
                plt.savefig(os.path.join(results_dir, f"Distribution plot of {col}.jpeg"), dpi=1000)
                # plt.show()

    return dist_dict, plot_data, plot_labels, div_data_dict, div_dict, mad_dict


def box_plot(data_for_analysis, config_file, analysis_frequency, show_plot=False,results_dir=None):
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

    legend_ref = str(ref_data['date'].iloc[0]) + " " + \
        'to' " " + str(ref_data['date'].iloc[-1])
    legend_comp = str(comp_data['date'].iloc[0]) + \
        " " + 'to'+" " + str(comp_data['date'].iloc[-1])

    feature_to_drop = analysis_frequency + \
        [config_file["defect_for_analysis"]+" "+"%"]

    ref_data = ref_data.drop(feature_to_drop, axis=1)
    comp_data = comp_data.drop(feature_to_drop, axis=1)

    summary_dict = {}
    box_dict = {}

    for col in ref_data.columns:
        if is_numeric_dtype(ref_data[col]):
            data1 = ref_data[col].to_frame()
            data1.index = range(len(data1))
            data1['date'] = legend_ref

            data2 = comp_data[col].to_frame()
            data2.index = range(len(data2))
            data2['date'] = legend_comp

            dfnew = pd.concat([data1, data2], axis=0)
            box_dict[col] = dfnew

            change = 100*(data1[col].median() -
                          data2[col].median())/data1[col].median()
            summary_dict[col] = round(abs(change), 2)

            if show_plot:
                fig = plt.figure(figsize=(config_file["figure_configuration"]["dist_plot"]["figsize"]
                                 [0], config_file["figure_configuration"]["dist_plot"]["figsize"][1]))
                title = 'Absolute change in' + " " + col + \
                    ":" + str(round(abs(change), 2)) + " " + "%"
                # .set(title=title,fontsize=20)###sns.boxplot(df1[item],color="r")
                fig = sns.boxplot(x='date', y=col, data=dfnew)
                fig.set_xlabel(
                    'Period', fontsize=config_file["figure_configuration"]["dist_plot"]["fontsize"])
                fig.set_ylabel(
                    col, fontsize=config_file["figure_configuration"]["box_plot"]["fontsize"])

                plt.title(
                    title, fontsize=config_file["figure_configuration"]["box_plot"]["title_fontsize"])
                fig.set_xticklabels(fig.get_xticklabels(), rotation=30, horizontalalignment='right',
                                    fontsize=6, fontweight='bold')
                if "/" in col:
                    col = col.replace("/", "_")
                plt.savefig(os.path.join(results_dir, f"Box plot of {col}.jpeg"), dpi=1000)
                # plt.show()

 
    return box_dict, summary_dict


def correlation_plot(data_for_analysis, config_file, analysis_frequency, show_plot=False,results_dir=None):
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

    legend_ref = str(ref_data['date'].iloc[0]) + " " + \
        'to' " " + str(ref_data['date'].iloc[-1])
    legend_comp = str(comp_data['date'].iloc[0]) + \
        " " + 'to'+" " + str(comp_data['date'].iloc[-1])

    feature_to_drop = analysis_frequency
    defect_type = config_file["defect_for_analysis"]
    rejection_field = defect_type + " "+"%"
    ref_data = ref_data.drop(feature_to_drop, axis=1)
    comp_data = comp_data.drop(feature_to_drop, axis=1)

    corr_dict = {}
    plot_labels = [legend_ref, legend_comp]
    for col in ref_data.columns:
        if is_numeric_dtype(ref_data[col]):
            if col not in [rejection_field]:
                data1 = ref_data[[col, rejection_field]]
                data2 = comp_data[[col, rejection_field]]
                corr_dict[col] = {}
                corr_dict[col]["data1"] = data1
                corr_dict[col]["data2"] = data2
                if show_plot:
                    # inside the loop
                    fig = plt.figure(figsize=(config_file["figure_configuration"]["dist_plot"]["figsize"]
                                            [0], config_file["figure_configuration"]["dist_plot"]["figsize"][1]))
                    fig = sns.scatterplot(
                        data1[col], data1[rejection_field], color="b", label=legend_ref)
                    fig = sns.scatterplot(
                        data2[col], data2[rejection_field], color="r", label=legend_comp)
                    plt.legend()
                    fig.set_xlabel(
                        col, fontsize=config_file["figure_configuration"]["correlation_plot"]["fontsize"])
                    fig.set_ylabel(
                        rejection_field, fontsize=config_file["figure_configuration"]["correlation_plot"]["fontsize"])
                    title = rejection_field + " "+'vs' + " " + col
                    plt.title(
                        title, fontsize=config_file["figure_configuration"]["correlation_plot"]["title_fontsize"])
                    plt.ylim(0,)

                    if "/" in col:
                        col = col.replace("/", "_")

                    if results_dir:
                        os.makedirs(results_dir, exist_ok=True)
                        plt.savefig(os.path.join(results_dir, f"Correlation plot of {col}.jpeg"), dpi=1000)
                    # plt.show()


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
    """
    if not isinstance(box_dict, dict):
        raise TypeError("box_dict must be a python dictionary")

    outlier_dict = {}
    cols = list(box_dict.keys())

    for col in cols:
        outlier_dict[col] = {}
        temp_df = box_dict[col]

        unique_dates = temp_df["date"].unique()

        if len(unique_dates) == 1:
            # Only one period available (same reference and comparison)
            single_date = unique_dates[0]
            df = temp_df[temp_df["date"] == single_date]

            lower_whisker, upper_whisker = whisker_calc(df[col])
            outlier_dict[col][single_date] = [lower_whisker, upper_whisker]

            print(f"[INFO] Only one period found for '{col}'. Outlier analysis done on single period: {single_date}")

        elif len(unique_dates) >= 2:
            ref_date = unique_dates[0]
            comp_date = unique_dates[1]

            ref_df = temp_df[temp_df["date"] == ref_date]
            comp_df = temp_df[temp_df["date"] == comp_date]

            lower_whisker_ref, upper_whisker_ref = whisker_calc(ref_df[col])
            lower_whisker_comp, upper_whisker_comp = whisker_calc(comp_df[col])

            outlier_dict[col][ref_date] = [lower_whisker_ref, upper_whisker_ref]
            outlier_dict[col][comp_date] = [lower_whisker_comp, upper_whisker_comp]

        else:
            print(f"[WARNING] No valid dates found for {col}. Skipping outlier calc.")
            continue

    return outlier_dict


def find_outliers(outlier_dict, box_dict):
    """
    Function to find the outliers for all the properties for
    reference and comparison data
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
        unique_dates = temp_df["date"].unique()

        if len(unique_dates) == 1:
            date = unique_dates[0]
            df = temp_df[temp_df["date"] == date]
            outlier = outlier_dict.get(col, {})
            if date in outlier:
                ref_outliers = list(df[(df[col] < outlier[date][0]) | (df[col] > outlier[date][1])][col].values.round(2))
            else:
                ref_outliers = []
            outliers[col][date] = ref_outliers
            print(f"[INFO] Single date period for {col}: Outliers checked for {date}")

        elif len(unique_dates) >= 2:
            ref_date = unique_dates[0]
            comp_date = unique_dates[1]

            ref_df = temp_df[temp_df["date"] == ref_date]
            comp_df = temp_df[temp_df["date"] == comp_date]
            outlier = outlier_dict.get(col, {})

            try:
                ref_outliers = list(ref_df[(ref_df[col] < outlier[ref_date][0]) | (ref_df[col] > outlier[ref_date][1])][col].values.round(2))
            except:
                ref_outliers = []

            try:
                comp_outliers = list(comp_df[(comp_df[col] < outlier[comp_date][0]) | (comp_df[col] > outlier[comp_date][1])][col].values.round(2))
            except:
                comp_outliers = []

            outliers[col][ref_date] = ref_outliers
            outliers[col][comp_date] = comp_outliers

        else:
            print(f"[WARNING] No date found for {col}. Skipping.")
            continue

    return outliers



# def product_mix_calculator(rej_data, config_file, grouping_info):
#     """
#     Function to calculate product mix based on reference and comparison period

#     Parameters
#     ----------
#     :param rej_data: Rejection dataframe
#     :type rej_data: pandas.DataFrame
#     :param config_file: Configuration file
#     :type config_file: dict

#     Returns
#     -------
#     :returns: Product mix dictionary
#     :rtype: dict
#     """

#     if not isinstance(rej_data, pd.DataFrame):
#         raise TypeError("rej_data must be a pandas DataFrame")
#     if not isinstance(config_file, dict):
#         raise TypeError("config_file must be a python dictionary")

#     rej_data = rej_data.rename(columns={"date": "date"})

#     rej_data['date'] = pd.to_datetime(rej_data['date'])
#     rej_data["prodn_wt"] = rej_data[config_file["total_produced_qty"]
#                                     ] * rej_data["Nett Casting Wt (Kg)"]

#     if config_file["group_wise_analysis"]:
#         agg_var = "group"
#         for key in list(grouping_info.keys()):
#             if key.lower() != "group_all":
#                 rej_data.loc[rej_data["component_id"].astype(str).isin(grouping_info[key]), agg_var] = key
#     elif config_file["component_wise_analysis"]:
#         agg_var = "comp"
#         if len(config_file["component_for_analysis"]) == 1:
#             if type(config_file["component_for_analysis"][0]) != str:
#                 comp_analysis = config_file["component_for_analysis"][0].astype(str)
#                 rej_data[agg_var] = np.where(rej_data["component_id"] == comp_analysis, comp_analysis, "")
#             else:
#                 comp_analysis = config_file["component_for_analysis"][0]
#                 rej_data[agg_var] = np.where(rej_data["component_id"] == comp_analysis, comp_analysis, "")
#         else:
#             raise ValueError("Only one component can be passed for analysis")
#         #rej_data[agg_var] = rej_data[rej_data["component_id"].isin(config_file["component_for_analysis"])]
#     else:
#         agg_var = "component_id"

#     rej_data = rej_data[["date", agg_var, "prodn_wt"]]
#     mask_ref = (rej_data['date'] >= config_file["data_selection"]["reference_period"][0]) & (
#         rej_data['date'] <= config_file["data_selection"]["reference_period"][1])
#     mask_compar = (rej_data['date'] >= config_file["data_selection"]["comparison_period"][0]) & (
#         rej_data['date'] <= config_file["data_selection"]["comparison_period"][1])
#     ref_data = rej_data[mask_ref]
#     ref_data['date'] = ref_data['date'].dt.date
#     ref_data.index = range(len(ref_data))

#     comp_data = rej_data[mask_compar]
#     comp_data['date'] = comp_data['date'].dt.date
#     comp_data.index = range(len(comp_data))

#     # if config_file["group_wise_analysis"] == False and config_file["component_wise_analysis"] == False:
#     #     tot_wt = ref_data["prodn_wt"].sum()

#     prod_mix_dict = {}
#     agg_ref = ref_data.groupby(agg_var, as_index=False)[
#         "prodn_wt"].sum()

#     agg_comp = comp_data.groupby(agg_var, as_index=False)[
#         "prodn_wt"].sum()
    
#     if (config_file["group_wise_analysis"] == False) and \
#         (config_file["component_wise_analysis"] == False):
#         top_n = config_file["top_n_components"]
#         top_n_comp = agg_ref.sort_values(by="prodn_wt", ascending=False)["component_id"][:top_n].values

#         for comp in list(top_n_comp):
#             try:
#                 val = round((agg_comp[agg_comp[agg_var] == comp]["prodn_wt"].values[0]-agg_ref[agg_ref[agg_var] == comp]
#                             ["prodn_wt"].values[0])/agg_ref[agg_ref[agg_var] == comp]
#                             ["prodn_wt"].values[0]*100, 2)
#             except IndexError:
#                 val = 0.0015
#             prod_mix_dict[str(comp)] = val

#     else:
#         for grp in list(agg_comp[agg_var].unique()):
#             if grp != "":
#                 val = round((agg_comp[agg_comp[agg_var] == grp]["prodn_wt"].values[0]-agg_ref[agg_ref[agg_var] == grp]
#                             ["prodn_wt"].values[0])/agg_ref[agg_ref[agg_var] == grp]
#                             ["prodn_wt"].values[0]*100, 2)
#                 prod_mix_dict[str(grp)] = val

#     return prod_mix_dict

def product_mix_calculator(rej_data, config_file, grouping_info):
    if not isinstance(rej_data, pd.DataFrame):
        raise TypeError("rej_data must be a pandas DataFrame")
    if not isinstance(config_file, dict):
        raise TypeError("config_file must be a dictionary")

    rej_data = rej_data.rename(columns={"date": "date"})
    rej_data["date"] = pd.to_datetime(rej_data["date"])
    rej_data["prodn_wt"] = rej_data[config_file["total_produced_qty"]] * rej_data["nett_casting_wt"]

    # Assign grouping key
    if config_file.get("group_wise_analysis", False):
        agg_var = "group"
        for group_name, comp_list in grouping_info.items():
            if group_name.lower() != "group_all":
                rej_data.loc[rej_data["component_id"].isin(comp_list), agg_var] = group_name

    elif config_file.get("component_wise_analysis", False):
        agg_var = "component_id"
        components = config_file.get("component_for_analysis", [])
        rej_data = rej_data[rej_data["component_id"].isin(components)]

    else:
        agg_var = "component_id"

    # Filter for required columns
    rej_data = rej_data[["date", agg_var, "prodn_wt"]]

    # Filter reference and comparison periods
    mask_ref = (rej_data["date"] >= config_file["data_selection"]["reference_period"][0]) & \
               (rej_data["date"] <= config_file["data_selection"]["reference_period"][1])
    mask_comp = (rej_data["date"] >= config_file["data_selection"]["comparison_period"][0]) & \
                (rej_data["date"] <= config_file["data_selection"]["comparison_period"][1])

    ref_data = rej_data[mask_ref].copy()
    comp_data = rej_data[mask_comp].copy()

    ref_data["date"] = ref_data["date"].dt.date
    comp_data["date"] = comp_data["date"].dt.date

    # Aggregate by group/component
    agg_ref = ref_data.groupby(agg_var)["prodn_wt"].sum().reset_index()
    agg_comp = comp_data.groupby(agg_var)["prodn_wt"].sum().reset_index()

    prod_mix_dict = {}

    if not config_file.get("group_wise_analysis", False) and not config_file.get("component_wise_analysis", False):
        # Default case: Top N components from reference period
        top_n = config_file.get("top_n_components", 10)
        top_components = agg_ref.sort_values("prodn_wt", ascending=False).head(top_n)[agg_var]

        for comp in top_components:
            ref_wt = agg_ref[agg_ref[agg_var] == comp]["prodn_wt"].values[0]
            comp_wt = agg_comp[agg_comp[agg_var] == comp]["prodn_wt"].values[0] if comp in agg_comp[agg_var].values else 0
            shift = round(((comp_wt - ref_wt) / ref_wt) * 100, 2)
            prod_mix_dict[str(comp)] = shift
    else:
        # Group-wise or multiple component-wise
        for item in agg_ref[agg_var].unique():
            ref_wt = agg_ref[agg_ref[agg_var] == item]["prodn_wt"].values[0]
            comp_wt = agg_comp[agg_comp[agg_var] == item]["prodn_wt"].values[0] if item in agg_comp[agg_var].values else 0
            shift = round(((comp_wt - ref_wt) / ref_wt) * 100, 2)
            prod_mix_dict[str(item)] = shift

    return prod_mix_dict




def enhanced_dist_plot(data_for_analysis, config_file, analysis_frequency, show_plot=False, results_dir=None):
    """
    Enhanced version of the distribution plot function for reference vs comparison data.

    Parameters
    ----------
    data_for_analysis : dict
        Dictionary with 'ref_data' and 'comp_data' DataFrames.

    config_file : dict
        Configuration including defect_for_analysis, figure_configuration etc.

    analysis_frequency : list
        List of column names to drop before plotting.

    show_plot : bool
        Whether to display plots in real-time.

    results_dir : str
        Directory to save plots.

    Returns
    -------
    dist_dict : dict
    plot_data : dict
    plot_labels : list
    div_data_dict : dict
    div_dict : dict
    mad_dict : dict
    """
    assert isinstance(data_for_analysis, dict), "data_for_analysis must be a dictionary"
    assert isinstance(analysis_frequency, list), "analysis_frequency must be a list"
    assert 'ref_data' in data_for_analysis and 'comp_data' in data_for_analysis, "Missing ref_data or comp_data"

    ref_data = data_for_analysis['ref_data'].copy()
    comp_data = data_for_analysis['comp_data'].copy()

    legend_ref = f"{ref_data['date'].iloc[0]} to {ref_data['date'].iloc[-1]}"
    legend_comp = f"{comp_data['date'].iloc[0]} to {comp_data['date'].iloc[-1]}"
    plot_labels = [legend_ref, legend_comp]

    feature_to_drop = analysis_frequency + [config_file["defect_for_analysis"] + " %"]
    ref_data.drop(columns=[col for col in feature_to_drop if col in ref_data], inplace=True, errors='ignore')
    comp_data.drop(columns=[col for col in feature_to_drop if col in comp_data], inplace=True, errors='ignore')

    dist_dict, plot_data, div_data_dict, div_dict, mad_dict = {}, {}, {}, {}, {}
    col_bins = [col for col in ref_data.columns if "bins" in col]

    # JS divergence computation for binned columns
    for bin_col in col_bins:
        ref_df = ref_data[bin_col].value_counts(normalize=True).rename("ref")
        comp_df = comp_data[bin_col].value_counts(normalize=True).rename("comp")
        binning_df = pd.concat([ref_df, comp_df], axis=1).fillna(0).sort_index()

        div_data_dict[bin_col] = binning_df
        div_dict[bin_col] = round(js(binning_df["ref"], binning_df["comp"]), 2)

    # KDE plots and MAD calculations
    for col in ref_data.columns:
        if is_numeric_dtype(ref_data[col]) and is_numeric_dtype(comp_data[col]):
            if ref_data[col].std() > 0.01 and comp_data[col].std() > 0.01:
                mad_ratio = round(mad(comp_data[col]) / mad(ref_data[col]), 2)
                mad_dict[col] = mad_ratio
            else:
                mad_dict[col] = np.nan

            dist_dict[col] = {
                "ref_data": ref_data[col],
                "comp_data": comp_data[col]
            }

            plot_data[col] = {}

            plt.figure(figsize=tuple(config_file["figure_configuration"]["dist_plot"]["figsize"]))
            sns.kdeplot(ref_data[col], shade=True, label=legend_ref)
            sns.kdeplot(comp_data[col], shade=True, label=legend_comp)

            plt.xlabel(col, fontsize=config_file["figure_configuration"]["dist_plot"]["fontsize"])
            plt.ylabel("Density", fontsize=config_file["figure_configuration"]["dist_plot"]["fontsize"])
            plt.title(f"Distribution plot of {col}", fontsize=config_file["figure_configuration"]["dist_plot"]["title_fontsize"])
            plt.legend(loc=config_file["figure_configuration"]["dist_plot"]["legend_location"])

            col_safe = col.replace("/", "_")
            if results_dir:
                os.makedirs(results_dir, exist_ok=True)
                plt.savefig(os.path.join(results_dir, f"Distribution Plot of {col_safe}.jpeg"), dpi=300)
            # if show_plot:
            #     # plt.show()
            plt.close()

    return dist_dict, plot_data, plot_labels, div_data_dict, div_dict, mad_dict





# def enhanced_dist_plot(data_for_analysis, config_file, analysis_frequency, show_plot=False, results_dir=None):
#     """
#     Enhanced version of the distribution plot function for reference vs comparison data.

#     Parameters
#     ----------
#     data_for_analysis : dict
#         Dictionary with 'ref_data' and 'comp_data' DataFrames.

#     config_file : dict
#         Configuration including defect_for_analysis, figure_configuration etc.

#     analysis_frequency : list
#         List of column names to drop before plotting.

#     show_plot : bool
#         Whether to display plots in real-time.

#     results_dir : str
#         Directory to save plots.

#     Returns
#     -------
#     dist_dict : dict
#     plot_data : dict
#     plot_labels : list
#     div_data_dict : dict
#     div_dict : dict
#     mad_dict : dict
#     """
#     assert isinstance(data_for_analysis, dict), "data_for_analysis must be a dictionary"
#     assert isinstance(analysis_frequency, list), "analysis_frequency must be a list"
#     assert 'ref_data' in data_for_analysis and 'comp_data' in data_for_analysis, "Missing ref_data or comp_data"

#     ref_data = data_for_analysis['ref_data'].copy()
#     comp_data = data_for_analysis['comp_data'].copy()

#     legend_ref = f"{ref_data['date'].iloc[0]} to {ref_data['date'].iloc[-1]}"
#     legend_comp = f"{comp_data['date'].iloc[0]} to {comp_data['date'].iloc[-1]}"
#     plot_labels = [legend_ref, legend_comp]

#     feature_to_drop = analysis_frequency + [config_file["defect_for_analysis"] + " %"]
#     ref_data.drop(columns=[col for col in feature_to_drop if col in ref_data], inplace=True, errors='ignore')
#     comp_data.drop(columns=[col for col in feature_to_drop if col in comp_data], inplace=True, errors='ignore')

#     dist_dict, plot_data, div_data_dict, div_dict, mad_dict = {}, {}, {}, {}, {}
#     col_bins = [col for col in ref_data.columns if "bins" in col]

#     # JS divergence computation for binned columns
#     for bin_col in col_bins:
#         ref_df = ref_data[bin_col].value_counts(normalize=True).rename("ref")
#         comp_df = comp_data[bin_col].value_counts(normalize=True).rename("comp")
#         binning_df = pd.concat([ref_df, comp_df], axis=1).fillna(0).sort_index()

#         div_data_dict[bin_col] = binning_df
#         div_dict[bin_col] = round(js(binning_df["ref"], binning_df["comp"]), 2)

#     # KDE plots and MAD calculations
    
#     for col in ref_data.columns:
#         if is_numeric_dtype(ref_data[col]) and is_numeric_dtype(comp_data[col]):
#             if ref_data[col].std() > 0.01 and comp_data[col].std() > 0.01:
#                 mad_ratio = round(mad(comp_data[col]) / mad(ref_data[col]), 2)
#                 mad_dict[col] = mad_ratio
#             else:
#                 mad_dict[col] = np.nan

#             dist_dict[col] = {
#                 "ref_data": ref_data[col],
#                 "comp_data": comp_data[col]
#             }

#             # Generate KDEs
#             ref_kde = sns.kdeplot(ref_data[col], bw_adjust=0.5).get_lines()[0].get_data()
#             plt.close()  # close seaborn plot to prevent rendering

#             comp_kde = sns.kdeplot(comp_data[col], bw_adjust=0.5).get_lines()[0].get_data()
#             plt.close()

#             # Create interactive plot using Plotly
#             fig = go.Figure()

#             fig.add_trace(go.Scatter(
#                 x=ref_kde[0],
#                 y=ref_kde[1],
#                 mode='lines',
#                 name='Reference',
#                 line=dict(color='red'),
#                 hovertemplate='Reference<br>Density: %{{y:.2f})<br>' + f'{col}: %{{x:.2f}}<extra></extra>'
#             ))

#             fig.add_trace(go.Scatter(
#                 x=comp_kde[0],
#                 y=comp_kde[1],
#                 mode='lines',
#                 name='Comparison',
#                 line=dict(color='blue'),
#                 hovertemplate='Comparison<br>Density: %{(y:.2f}}<br>' + f'{col}: %{{x:.2f}}<extra></extra>'
#             ))

#             fig.update_layout(
#                 title=f"Distribution Plot of {col}",
#                 xaxis_title=col,
#                 yaxis_title="Density",
#                 legend=dict(x=0.8, y=0.95),
#                 template="simple_white"
#             )

#             if results_dir:
#                 os.makedirs(results_dir, exist_ok=True)
#                 pio.write_image(fig, os.path.join(results_dir, f"Distribution plot of {col}.svg"), scale=2)

#             if show_plot:
#                 fig.show()
#     return dist_dict, plot_data, plot_labels, div_data_dict, div_dict, mad_dict




