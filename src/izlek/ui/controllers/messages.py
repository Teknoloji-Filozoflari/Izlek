"""Short, safe user-facing messages for controller failures."""

from izlek.i18n import t


def network_unavailable() -> str:
    return t("errors.network")


def local_data_unavailable() -> str:
    return t("errors.local_data")


def file_operation_failed() -> str:
    return t("errors.file_operation")
