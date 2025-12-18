"""
TPC-H column and scale factor mappings.

Provides mappings between Trino's tpch connector names and TPC-H standard names.
"""

import re
from typing import Optional

# Map dataset names to TPC-H scale factors
TPCH_SCALE_FACTOR_MAP = {
    'tpch-tiny': 'tiny',
    'tpch-sf0_01': 'tiny',  # ~0.01 SF maps to tiny
    'tpch-sf0.01': 'tiny',
    'tpch-sf1': 'sf1',
    'tpch-sf10': 'sf10',
    'tpch-sf100': 'sf100',
}

# Column mappings from Trino's tpch connector to TPC-H standard names
# Trino uses short names, TPC-H standard uses prefix (l_, o_, c_, etc.)
TPCH_COLUMN_MAPPINGS = {
    'nation': {
        'nationkey': 'n_nationkey',
        'name': 'n_name',
        'regionkey': 'n_regionkey',
        'comment': 'n_comment',
    },
    'region': {
        'regionkey': 'r_regionkey',
        'name': 'r_name',
        'comment': 'r_comment',
    },
    'customer': {
        'custkey': 'c_custkey',
        'name': 'c_name',
        'address': 'c_address',
        'nationkey': 'c_nationkey',
        'phone': 'c_phone',
        'acctbal': 'c_acctbal',
        'mktsegment': 'c_mktsegment',
        'comment': 'c_comment',
    },
    'supplier': {
        'suppkey': 's_suppkey',
        'name': 's_name',
        'address': 's_address',
        'nationkey': 's_nationkey',
        'phone': 's_phone',
        'acctbal': 's_acctbal',
        'comment': 's_comment',
    },
    'part': {
        'partkey': 'p_partkey',
        'name': 'p_name',
        'mfgr': 'p_mfgr',
        'brand': 'p_brand',
        'type': 'p_type',
        'size': 'p_size',
        'container': 'p_container',
        'retailprice': 'p_retailprice',
        'comment': 'p_comment',
    },
    'partsupp': {
        'partkey': 'ps_partkey',
        'suppkey': 'ps_suppkey',
        'availqty': 'ps_availqty',
        'supplycost': 'ps_supplycost',
        'comment': 'ps_comment',
    },
    'orders': {
        'orderkey': 'o_orderkey',
        'custkey': 'o_custkey',
        'orderstatus': 'o_orderstatus',
        'totalprice': 'o_totalprice',
        'orderdate': 'o_orderdate',
        'orderpriority': 'o_orderpriority',
        'clerk': 'o_clerk',
        'shippriority': 'o_shippriority',
        'comment': 'o_comment',
    },
    'lineitem': {
        'orderkey': 'l_orderkey',
        'partkey': 'l_partkey',
        'suppkey': 'l_suppkey',
        'linenumber': 'l_linenumber',
        'quantity': 'l_quantity',
        'extendedprice': 'l_extendedprice',
        'discount': 'l_discount',
        'tax': 'l_tax',
        'returnflag': 'l_returnflag',
        'linestatus': 'l_linestatus',
        'shipdate': 'l_shipdate',
        'commitdate': 'l_commitdate',
        'receiptdate': 'l_receiptdate',
        'shipinstruct': 'l_shipinstruct',
        'shipmode': 'l_shipmode',
        'comment': 'l_comment',
    },
}


def get_tpch_scale_factor(dataset_name: str) -> Optional[str]:
    """
    Map dataset name to TPC-H scale factor schema.
    
    Args:
        dataset_name: Dataset name (e.g., 'tpch-tiny', 'tpch-sf1')
    
    Returns:
        Schema name in tpch catalog (e.g., 'tiny', 'sf1') or None
    """
    # Direct mapping
    if dataset_name in TPCH_SCALE_FACTOR_MAP:
        return TPCH_SCALE_FACTOR_MAP[dataset_name]
    
    # Try to extract scale factor from name
    match = re.search(r'sf(\d+)', dataset_name.lower())
    if match:
        sf = match.group(1)
        return f'sf{sf}'
    
    if 'tiny' in dataset_name.lower():
        return 'tiny'
    
    return None


def get_column_mappings(table_name: str) -> dict:
    """
    Get column mappings for a TPC-H table.
    
    Args:
        table_name: Table name
    
    Returns:
        Dict mapping Trino tpch column names to TPC-H standard names
    """
    return TPCH_COLUMN_MAPPINGS.get(table_name, {})
