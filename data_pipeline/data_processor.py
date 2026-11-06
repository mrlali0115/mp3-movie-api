# data_processor.py
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def remove_duplicates(df):
    """Remove duplicate rows."""
    before = len(df)
    df = df.drop_duplicates()
    logger.debug(f"remove_duplicates: {before} → {len(df)} rows")
    return df


def handle_missing(df, axis="rows"):
    """Drop rows or columns containing missing values."""
    supported_axes = ["rows", "columns"]
    if axis not in supported_axes:
        logger.error(f"Unsupported axis: {axis}")
        raise ValueError(f"Unsupported axis: {axis}")

    if axis == "rows":
        before = df.shape[0]
        df = df.dropna()
        logger.debug(f"handle_missing: {before} → {df.shape[0]} rows")
    else:
        before = df.shape[1]
        df = df.dropna(axis=1)
        logger.debug(f"handle_missing: {before} → {df.shape[1]} columns")

    return df


def remove_outliers(df, columns, method, threshold):
    """Remove outliers from the specified numeric columns."""
    supported_methods = ["iqr", "zscore"]
    if method not in supported_methods:
        logger.error(f"Unsupported outlier method: {method}")
        raise ValueError(f"Unsupported outlier method: {method}")

    logger.debug(f"remove_outliers: method={method}, threshold={threshold}")

    for column in columns:
        if column not in df.columns:
            logger.warning(f"Column not found: {column}")
            continue

        if not pd.api.types.is_numeric_dtype(df[column]):
            logger.warning(f"Column is not numeric: {column}")
            continue

        before = len(df)

        if method == "iqr":
            q1 = df[column].quantile(0.25)
            q3 = df[column].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - threshold * iqr
            upper = q3 + threshold * iqr
            df = df[(df[column] >= lower) & (df[column] <= upper)]
            logger.debug(
                f"{column}: lower={lower}, upper={upper}, removed={before - len(df)}"
            )
        else:
            mean = df[column].mean()
            std = df[column].std()
            z_scores = (df[column] - mean) / std
            df = df[z_scores.abs() <= threshold]
            logger.debug(
                f"{column}: mean={mean}, std={std}, removed={before - len(df)}"
            )

    return df


def process_data(df, config):
    """Apply the processing steps enabled in the configuration."""
    processing = config["processing"]

    # 1. Remove duplicates
    if processing["remove_duplicates"]:
        df = remove_duplicates(df)

    # 2. Handle missing values
    if processing["missing"]["enabled"]:
        df = handle_missing(df, processing["missing"]["axis"])

    # 3. Remove outliers
    if processing["outliers"]["enabled"]:
        df = remove_outliers(
            df,
            processing["outliers"]["columns"],
            processing["outliers"]["method"],
            processing["outliers"]["threshold"],
        )

    return df


def create_cleaning_report(df_before, df_after):
    """Return a dictionary summarizing the cleaning results."""
    report = {
        "rows_before": df_before.shape[0],
        "rows_after": df_after.shape[0],
        "rows_removed": df_before.shape[0] - df_after.shape[0],
        "columns_before": df_before.shape[1],
        "columns_after": df_after.shape[1],
        "columns_removed": df_before.shape[1] - df_after.shape[1],
    }
    return report