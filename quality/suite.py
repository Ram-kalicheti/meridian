from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from quality.checks import (
    check_chunk_id_uniqueness,
    check_schema_validation,
)
from quality.schema import (
    ALLOWED_DOC_TYPES,
    CONTENT_LENGTH_MAX,
    CONTENT_LENGTH_MIN,
    REQUIRED_NON_NULL_COLS,
)

_BATCH_CHECKS = [
    ("schema_validation", check_schema_validation),
    ("chunk_id_uniqueness", check_chunk_id_uniqueness),
]

_DQ_ERROR_TYPE = "_dq_error_type"
_DQ_ERROR_REASON = "_dq_error_reason"


def run_suite(df: DataFrame) -> tuple[DataFrame, DataFrame]:
    """
    Batch-level checks fail the entire DataFrame and partial silver writes
    with schema drift or duplicate keys cause silent corruption downstream.
    Row-level checks quarantine individual rows; clean rows still reach silver.
    """
    spark = df.sparkSession

    for check_name, check_fn in _BATCH_CHECKS:
        passed, reason = check_fn(df)
        if not passed:
            rejected = (
                df.withColumn("error_type", F.lit(check_name))
                .withColumn("error_reason", F.lit(reason))
            )
            empty = spark.createDataFrame([], df.schema)
            return empty, rejected

    df = df.withColumn(_DQ_ERROR_TYPE, F.lit(None).cast("string")).withColumn(
        _DQ_ERROR_REASON, F.lit(None).cast("string")
    )

    df = _tag_null_completeness(df)
    df = _tag_content_length(df)
    df = _tag_section_count(df)
    df = _tag_doc_type_enum(df)

    passed_df = df.filter(F.col(_DQ_ERROR_TYPE).isNull()).drop(
        _DQ_ERROR_TYPE, _DQ_ERROR_REASON
    )

    rejected_df = (
        df.filter(F.col(_DQ_ERROR_TYPE).isNotNull())
        .withColumnRenamed(_DQ_ERROR_TYPE, "error_type")
        .withColumnRenamed(_DQ_ERROR_REASON, "error_reason")
    )

    return passed_df, rejected_df


def _tag_null_completeness(df: DataFrame) -> DataFrame:
    null_cond = F.lit(False)
    for col_name in REQUIRED_NON_NULL_COLS:
        null_cond = null_cond | F.col(col_name).isNull()

    return df.withColumn(
        _DQ_ERROR_TYPE,
        F.when(F.col(_DQ_ERROR_TYPE).isNull() & null_cond, F.lit("null_completeness")).otherwise(
            F.col(_DQ_ERROR_TYPE)
        ),
    ).withColumn(
        _DQ_ERROR_REASON,
        F.when(
            F.col(_DQ_ERROR_TYPE) == "null_completeness",
            F.lit("null value in required column"),
        ).otherwise(F.col(_DQ_ERROR_REASON)),
    )


def _tag_content_length(df: DataFrame) -> DataFrame:
    length_cond = (F.length(F.col("content")) < CONTENT_LENGTH_MIN) | (
        F.length(F.col("content")) > CONTENT_LENGTH_MAX
    )

    return df.withColumn(
        _DQ_ERROR_TYPE,
        F.when(F.col(_DQ_ERROR_TYPE).isNull() & length_cond, F.lit("content_length")).otherwise(
            F.col(_DQ_ERROR_TYPE)
        ),
    ).withColumn(
        _DQ_ERROR_REASON,
        F.when(
            F.col(_DQ_ERROR_TYPE) == "content_length",
            F.concat(
                F.lit("content length "),
                F.length(F.col("content")).cast("string"),
                F.lit(f" outside [{CONTENT_LENGTH_MIN}, {CONTENT_LENGTH_MAX}]"),
            ),
        ).otherwise(F.col(_DQ_ERROR_REASON)),
    )


def _tag_section_count(df: DataFrame) -> DataFrame:
    sc_cond = F.col("section_count") <= 0

    return df.withColumn(
        _DQ_ERROR_TYPE,
        F.when(
            F.col(_DQ_ERROR_TYPE).isNull() & sc_cond, F.lit("section_count_positive")
        ).otherwise(F.col(_DQ_ERROR_TYPE)),
    ).withColumn(
        _DQ_ERROR_REASON,
        F.when(
            F.col(_DQ_ERROR_TYPE) == "section_count_positive",
            F.concat(F.lit("section_count "), F.col("section_count").cast("string"), F.lit(" <= 0")),
        ).otherwise(F.col(_DQ_ERROR_REASON)),
    )


def _tag_doc_type_enum(df: DataFrame) -> DataFrame:
    enum_cond = ~F.col("doc_type").isin(list(ALLOWED_DOC_TYPES))

    return df.withColumn(
        _DQ_ERROR_TYPE,
        F.when(F.col(_DQ_ERROR_TYPE).isNull() & enum_cond, F.lit("doc_type_enum")).otherwise(
            F.col(_DQ_ERROR_TYPE)
        ),
    ).withColumn(
        _DQ_ERROR_REASON,
        F.when(
            F.col(_DQ_ERROR_TYPE) == "doc_type_enum",
            F.concat(F.lit("invalid doc_type: "), F.col("doc_type")),
        ).otherwise(F.col(_DQ_ERROR_REASON)),
    )