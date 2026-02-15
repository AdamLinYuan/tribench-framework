"""
Schema abstraction layer for benchmark datasets.

Provides polymorphic interfaces for different benchmark types (TPC-H, TPC-DS, etc.).
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict

import pyarrow as pa

logger = logging.getLogger(__name__)


class BenchmarkType(Enum):
    """Supported benchmark types."""
    TPCH = "tpch"
    TPCDS = "tpcds"


class DatasetSchema(ABC):
    """
    Abstract base class for dataset schemas.
    
    This provides a polymorphic interface for different benchmark types
    (TPC-H, TPC-DS, etc.) to define their table structures without hardcoding.
    """
    
    @abstractmethod
    def get_benchmark_type(self) -> BenchmarkType:
        """Return the benchmark type this schema represents."""
        pass
    
    @abstractmethod
    def get_tables(self) -> List[str]:
        """Return list of table names in this benchmark."""
        pass
    
    @abstractmethod
    def get_schema(self, table_name: str) -> pa.Schema:
        """
        Return PyArrow schema for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            PyArrow schema defining columns and types
            
        Raises:
            KeyError: If table_name is not valid for this benchmark
        """
        pass


class TPCHSchema(DatasetSchema):
    """TPC-H benchmark schema definitions."""
    
    def get_benchmark_type(self) -> BenchmarkType:
        return BenchmarkType.TPCH
    
    def get_tables(self) -> List[str]:
        return [
            'nation', 'region', 'customer', 'supplier',
            'part', 'partsupp', 'orders', 'lineitem'
        ]
    
    def get_schema(self, table_name: str) -> pa.Schema:
        """Get PyArrow schema for TPC-H tables."""
        schemas = {
            'nation': pa.schema([
                ('n_nationkey', pa.int32()),
                ('n_name', pa.string()),
                ('n_regionkey', pa.int32()),
                ('n_comment', pa.string())
            ]),
            'region': pa.schema([
                ('r_regionkey', pa.int32()),
                ('r_name', pa.string()),
                ('r_comment', pa.string())
            ]),
            'customer': pa.schema([
                ('c_custkey', pa.int32()),
                ('c_name', pa.string()),
                ('c_address', pa.string()),
                ('c_nationkey', pa.int32()),
                ('c_phone', pa.string()),
                ('c_acctbal', pa.decimal128(15, 2)),
                ('c_mktsegment', pa.string()),
                ('c_comment', pa.string())
            ]),
            'supplier': pa.schema([
                ('s_suppkey', pa.int32()),
                ('s_name', pa.string()),
                ('s_address', pa.string()),
                ('s_nationkey', pa.int32()),
                ('s_phone', pa.string()),
                ('s_acctbal', pa.decimal128(15, 2)),
                ('s_comment', pa.string())
            ]),
            'part': pa.schema([
                ('p_partkey', pa.int32()),
                ('p_name', pa.string()),
                ('p_mfgr', pa.string()),
                ('p_brand', pa.string()),
                ('p_type', pa.string()),
                ('p_size', pa.int32()),
                ('p_container', pa.string()),
                ('p_retailprice', pa.decimal128(15, 2)),
                ('p_comment', pa.string())
            ]),
            'partsupp': pa.schema([
                ('ps_partkey', pa.int32()),
                ('ps_suppkey', pa.int32()),
                ('ps_availqty', pa.int32()),
                ('ps_supplycost', pa.decimal128(15, 2)),
                ('ps_comment', pa.string())
            ]),
            'orders': pa.schema([
                ('o_orderkey', pa.int32()),
                ('o_custkey', pa.int32()),
                ('o_orderstatus', pa.string()),
                ('o_totalprice', pa.decimal128(15, 2)),
                ('o_orderdate', pa.date32()),
                ('o_orderpriority', pa.string()),
                ('o_clerk', pa.string()),
                ('o_shippriority', pa.int32()),
                ('o_comment', pa.string())
            ]),
            'lineitem': pa.schema([
                ('l_orderkey', pa.int32()),
                ('l_partkey', pa.int32()),
                ('l_suppkey', pa.int32()),
                ('l_linenumber', pa.int32()),
                ('l_quantity', pa.decimal128(15, 2)),
                ('l_extendedprice', pa.decimal128(15, 2)),
                ('l_discount', pa.decimal128(15, 2)),
                ('l_tax', pa.decimal128(15, 2)),
                ('l_returnflag', pa.string()),
                ('l_linestatus', pa.string()),
                ('l_shipdate', pa.date32()),
                ('l_commitdate', pa.date32()),
                ('l_receiptdate', pa.date32()),
                ('l_shipinstruct', pa.string()),
                ('l_shipmode', pa.string()),
                ('l_comment', pa.string())
            ])
        }
        
        if table_name not in schemas:
            raise KeyError(f"Unknown TPC-H table: {table_name}")
        
        return schemas[table_name]


class TPCDSSchema(DatasetSchema):
    """
    TPC-DS benchmark schema definitions (stub for future implementation).
    
    TPC-DS is a decision support benchmark with 24 tables.
    This is a placeholder for future TPC-DS support.
    """
    
    def get_benchmark_type(self) -> BenchmarkType:
        return BenchmarkType.TPCDS
    
    def get_tables(self) -> List[str]:
        # TPC-DS has 24 tables - these are the main fact tables
        return [
            'store_sales', 'store_returns', 'catalog_sales', 'catalog_returns',
            'web_sales', 'web_returns', 'inventory',
            'store', 'call_center', 'catalog_page', 'web_site', 'web_page',
            'warehouse', 'customer', 'customer_address', 'customer_demographics',
            'date_dim', 'household_demographics', 'item', 'income_band',
            'promotion', 'reason', 'ship_mode', 'time_dim'
        ]
    
    def get_schema(self, table_name: str) -> pa.Schema:
        """
        Get PyArrow schema for TPC-DS tables.
        
        Schemas based on TPC-DS v3.2.0 specification.
        """
        schemas = {
            # Fact Tables
            'store_sales': pa.schema([
                ('ss_sold_date_sk', pa.int32()),
                ('ss_sold_time_sk', pa.int32()),
                ('ss_item_sk', pa.int32()),
                ('ss_customer_sk', pa.int32()),
                ('ss_cdemo_sk', pa.int32()),
                ('ss_hdemo_sk', pa.int32()),
                ('ss_addr_sk', pa.int32()),
                ('ss_store_sk', pa.int32()),
                ('ss_promo_sk', pa.int32()),
                ('ss_ticket_number', pa.int64()),
                ('ss_quantity', pa.int32()),
                ('ss_wholesale_cost', pa.decimal128(7, 2)),
                ('ss_list_price', pa.decimal128(7, 2)),
                ('ss_sales_price', pa.decimal128(7, 2)),
                ('ss_ext_discount_amt', pa.decimal128(7, 2)),
                ('ss_ext_sales_price', pa.decimal128(7, 2)),
                ('ss_ext_wholesale_cost', pa.decimal128(7, 2)),
                ('ss_ext_list_price', pa.decimal128(7, 2)),
                ('ss_ext_tax', pa.decimal128(7, 2)),
                ('ss_coupon_amt', pa.decimal128(7, 2)),
                ('ss_net_paid', pa.decimal128(7, 2)),
                ('ss_net_paid_inc_tax', pa.decimal128(7, 2)),
                ('ss_net_profit', pa.decimal128(7, 2))
            ]),
            'store_returns': pa.schema([
                ('sr_returned_date_sk', pa.int32()),
                ('sr_return_time_sk', pa.int32()),
                ('sr_item_sk', pa.int32()),
                ('sr_customer_sk', pa.int32()),
                ('sr_cdemo_sk', pa.int32()),
                ('sr_hdemo_sk', pa.int32()),
                ('sr_addr_sk', pa.int32()),
                ('sr_store_sk', pa.int32()),
                ('sr_reason_sk', pa.int32()),
                ('sr_ticket_number', pa.int64()),
                ('sr_return_quantity', pa.int32()),
                ('sr_return_amt', pa.decimal128(7, 2)),
                ('sr_return_tax', pa.decimal128(7, 2)),
                ('sr_return_amt_inc_tax', pa.decimal128(7, 2)),
                ('sr_fee', pa.decimal128(7, 2)),
                ('sr_return_ship_cost', pa.decimal128(7, 2)),
                ('sr_refunded_cash', pa.decimal128(7, 2)),
                ('sr_reversed_charge', pa.decimal128(7, 2)),
                ('sr_store_credit', pa.decimal128(7, 2)),
                ('sr_net_loss', pa.decimal128(7, 2))
            ]),
            'catalog_sales': pa.schema([
                ('cs_sold_date_sk', pa.int32()),
                ('cs_sold_time_sk', pa.int32()),
                ('cs_ship_date_sk', pa.int32()),
                ('cs_bill_customer_sk', pa.int32()),
                ('cs_bill_cdemo_sk', pa.int32()),
                ('cs_bill_hdemo_sk', pa.int32()),
                ('cs_bill_addr_sk', pa.int32()),
                ('cs_ship_customer_sk', pa.int32()),
                ('cs_ship_cdemo_sk', pa.int32()),
                ('cs_ship_hdemo_sk', pa.int32()),
                ('cs_ship_addr_sk', pa.int32()),
                ('cs_call_center_sk', pa.int32()),
                ('cs_catalog_page_sk', pa.int32()),
                ('cs_ship_mode_sk', pa.int32()),
                ('cs_warehouse_sk', pa.int32()),
                ('cs_item_sk', pa.int32()),
                ('cs_promo_sk', pa.int32()),
                ('cs_order_number', pa.int64()),
                ('cs_quantity', pa.int32()),
                ('cs_wholesale_cost', pa.decimal128(7, 2)),
                ('cs_list_price', pa.decimal128(7, 2)),
                ('cs_sales_price', pa.decimal128(7, 2)),
                ('cs_ext_discount_amt', pa.decimal128(7, 2)),
                ('cs_ext_sales_price', pa.decimal128(7, 2)),
                ('cs_ext_wholesale_cost', pa.decimal128(7, 2)),
                ('cs_ext_list_price', pa.decimal128(7, 2)),
                ('cs_ext_tax', pa.decimal128(7, 2)),
                ('cs_coupon_amt', pa.decimal128(7, 2)),
                ('cs_ext_ship_cost', pa.decimal128(7, 2)),
                ('cs_net_paid', pa.decimal128(7, 2)),
                ('cs_net_paid_inc_tax', pa.decimal128(7, 2)),
                ('cs_net_paid_inc_ship', pa.decimal128(7, 2)),
                ('cs_net_paid_inc_ship_tax', pa.decimal128(7, 2)),
                ('cs_net_profit', pa.decimal128(7, 2))
            ]),
            'catalog_returns': pa.schema([
                ('cr_returned_date_sk', pa.int32()),
                ('cr_returned_time_sk', pa.int32()),
                ('cr_item_sk', pa.int32()),
                ('cr_refunded_customer_sk', pa.int32()),
                ('cr_refunded_cdemo_sk', pa.int32()),
                ('cr_refunded_hdemo_sk', pa.int32()),
                ('cr_refunded_addr_sk', pa.int32()),
                ('cr_returning_customer_sk', pa.int32()),
                ('cr_returning_cdemo_sk', pa.int32()),
                ('cr_returning_hdemo_sk', pa.int32()),
                ('cr_returning_addr_sk', pa.int32()),
                ('cr_call_center_sk', pa.int32()),
                ('cr_catalog_page_sk', pa.int32()),
                ('cr_ship_mode_sk', pa.int32()),
                ('cr_warehouse_sk', pa.int32()),
                ('cr_reason_sk', pa.int32()),
                ('cr_order_number', pa.int64()),
                ('cr_return_quantity', pa.int32()),
                ('cr_return_amount', pa.decimal128(7, 2)),
                ('cr_return_tax', pa.decimal128(7, 2)),
                ('cr_return_amt_inc_tax', pa.decimal128(7, 2)),
                ('cr_fee', pa.decimal128(7, 2)),
                ('cr_return_ship_cost', pa.decimal128(7, 2)),
                ('cr_refunded_cash', pa.decimal128(7, 2)),
                ('cr_reversed_charge', pa.decimal128(7, 2)),
                ('cr_store_credit', pa.decimal128(7, 2)),
                ('cr_net_loss', pa.decimal128(7, 2))
            ]),
            'web_sales': pa.schema([
                ('ws_sold_date_sk', pa.int32()),
                ('ws_sold_time_sk', pa.int32()),
                ('ws_ship_date_sk', pa.int32()),
                ('ws_item_sk', pa.int32()),
                ('ws_bill_customer_sk', pa.int32()),
                ('ws_bill_cdemo_sk', pa.int32()),
                ('ws_bill_hdemo_sk', pa.int32()),
                ('ws_bill_addr_sk', pa.int32()),
                ('ws_ship_customer_sk', pa.int32()),
                ('ws_ship_cdemo_sk', pa.int32()),
                ('ws_ship_hdemo_sk', pa.int32()),
                ('ws_ship_addr_sk', pa.int32()),
                ('ws_web_page_sk', pa.int32()),
                ('ws_web_site_sk', pa.int32()),
                ('ws_ship_mode_sk', pa.int32()),
                ('ws_warehouse_sk', pa.int32()),
                ('ws_promo_sk', pa.int32()),
                ('ws_order_number', pa.int64()),
                ('ws_quantity', pa.int32()),
                ('ws_wholesale_cost', pa.decimal128(7, 2)),
                ('ws_list_price', pa.decimal128(7, 2)),
                ('ws_sales_price', pa.decimal128(7, 2)),
                ('ws_ext_discount_amt', pa.decimal128(7, 2)),
                ('ws_ext_sales_price', pa.decimal128(7, 2)),
                ('ws_ext_wholesale_cost', pa.decimal128(7, 2)),
                ('ws_ext_list_price', pa.decimal128(7, 2)),
                ('ws_ext_tax', pa.decimal128(7, 2)),
                ('ws_coupon_amt', pa.decimal128(7, 2)),
                ('ws_ext_ship_cost', pa.decimal128(7, 2)),
                ('ws_net_paid', pa.decimal128(7, 2)),
                ('ws_net_paid_inc_tax', pa.decimal128(7, 2)),
                ('ws_net_paid_inc_ship', pa.decimal128(7, 2)),
                ('ws_net_paid_inc_ship_tax', pa.decimal128(7, 2)),
                ('ws_net_profit', pa.decimal128(7, 2))
            ]),
            'web_returns': pa.schema([
                ('wr_returned_date_sk', pa.int32()),
                ('wr_returned_time_sk', pa.int32()),
                ('wr_item_sk', pa.int32()),
                ('wr_refunded_customer_sk', pa.int32()),
                ('wr_refunded_cdemo_sk', pa.int32()),
                ('wr_refunded_hdemo_sk', pa.int32()),
                ('wr_refunded_addr_sk', pa.int32()),
                ('wr_returning_customer_sk', pa.int32()),
                ('wr_returning_cdemo_sk', pa.int32()),
                ('wr_returning_hdemo_sk', pa.int32()),
                ('wr_returning_addr_sk', pa.int32()),
                ('wr_web_page_sk', pa.int32()),
                ('wr_reason_sk', pa.int32()),
                ('wr_order_number', pa.int64()),
                ('wr_return_quantity', pa.int32()),
                ('wr_return_amt', pa.decimal128(7, 2)),
                ('wr_return_tax', pa.decimal128(7, 2)),
                ('wr_return_amt_inc_tax', pa.decimal128(7, 2)),
                ('wr_fee', pa.decimal128(7, 2)),
                ('wr_return_ship_cost', pa.decimal128(7, 2)),
                ('wr_refunded_cash', pa.decimal128(7, 2)),
                ('wr_reversed_charge', pa.decimal128(7, 2)),
                ('wr_account_credit', pa.decimal128(7, 2)),
                ('wr_net_loss', pa.decimal128(7, 2))
            ]),
            'inventory': pa.schema([
                ('inv_date_sk', pa.int32()),
                ('inv_item_sk', pa.int32()),
                ('inv_warehouse_sk', pa.int32()),
                ('inv_quantity_on_hand', pa.int32())
            ]),
            # Dimension Tables
            'store': pa.schema([
                ('s_store_sk', pa.int32()),
                ('s_store_id', pa.string()),
                ('s_rec_start_date', pa.date32()),
                ('s_rec_end_date', pa.date32()),
                ('s_closed_date_sk', pa.int32()),
                ('s_store_name', pa.string()),
                ('s_number_employees', pa.int32()),
                ('s_floor_space', pa.int32()),
                ('s_hours', pa.string()),
                ('s_manager', pa.string()),
                ('s_market_id', pa.int32()),
                ('s_geography_class', pa.string()),
                ('s_market_desc', pa.string()),
                ('s_market_manager', pa.string()),
                ('s_division_id', pa.int32()),
                ('s_division_name', pa.string()),
                ('s_company_id', pa.int32()),
                ('s_company_name', pa.string()),
                ('s_street_number', pa.string()),
                ('s_street_name', pa.string()),
                ('s_street_type', pa.string()),
                ('s_suite_number', pa.string()),
                ('s_city', pa.string()),
                ('s_county', pa.string()),
                ('s_state', pa.string()),
                ('s_zip', pa.string()),
                ('s_country', pa.string()),
                ('s_gmt_offset', pa.decimal128(5, 2)),
                ('s_tax_precentage', pa.decimal128(5, 2))
            ]),
            'call_center': pa.schema([
                ('cc_call_center_sk', pa.int32()),
                ('cc_call_center_id', pa.string()),
                ('cc_rec_start_date', pa.date32()),
                ('cc_rec_end_date', pa.date32()),
                ('cc_closed_date_sk', pa.int32()),
                ('cc_open_date_sk', pa.int32()),
                ('cc_name', pa.string()),
                ('cc_class', pa.string()),
                ('cc_employees', pa.int32()),
                ('cc_sq_ft', pa.int32()),
                ('cc_hours', pa.string()),
                ('cc_manager', pa.string()),
                ('cc_mkt_id', pa.int32()),
                ('cc_mkt_class', pa.string()),
                ('cc_mkt_desc', pa.string()),
                ('cc_market_manager', pa.string()),
                ('cc_division', pa.int32()),
                ('cc_division_name', pa.string()),
                ('cc_company', pa.int32()),
                ('cc_company_name', pa.string()),
                ('cc_street_number', pa.string()),
                ('cc_street_name', pa.string()),
                ('cc_street_type', pa.string()),
                ('cc_suite_number', pa.string()),
                ('cc_city', pa.string()),
                ('cc_county', pa.string()),
                ('cc_state', pa.string()),
                ('cc_zip', pa.string()),
                ('cc_country', pa.string()),
                ('cc_gmt_offset', pa.decimal128(5, 2)),
                ('cc_tax_percentage', pa.decimal128(5, 2))
            ]),
            'catalog_page': pa.schema([
                ('cp_catalog_page_sk', pa.int32()),
                ('cp_catalog_page_id', pa.string()),
                ('cp_start_date_sk', pa.int32()),
                ('cp_end_date_sk', pa.int32()),
                ('cp_department', pa.string()),
                ('cp_catalog_number', pa.int32()),
                ('cp_catalog_page_number', pa.int32()),
                ('cp_description', pa.string()),
                ('cp_type', pa.string())
            ]),
            'web_site': pa.schema([
                ('web_site_sk', pa.int32()),
                ('web_site_id', pa.string()),
                ('web_rec_start_date', pa.date32()),
                ('web_rec_end_date', pa.date32()),
                ('web_name', pa.string()),
                ('web_open_date_sk', pa.int32()),
                ('web_close_date_sk', pa.int32()),
                ('web_class', pa.string()),
                ('web_manager', pa.string()),
                ('web_mkt_id', pa.int32()),
                ('web_mkt_class', pa.string()),
                ('web_mkt_desc', pa.string()),
                ('web_market_manager', pa.string()),
                ('web_company_id', pa.int32()),
                ('web_company_name', pa.string()),
                ('web_street_number', pa.string()),
                ('web_street_name', pa.string()),
                ('web_street_type', pa.string()),
                ('web_suite_number', pa.string()),
                ('web_city', pa.string()),
                ('web_county', pa.string()),
                ('web_state', pa.string()),
                ('web_zip', pa.string()),
                ('web_country', pa.string()),
                ('web_gmt_offset', pa.decimal128(5, 2)),
                ('web_tax_percentage', pa.decimal128(5, 2))
            ]),
            'web_page': pa.schema([
                ('wp_web_page_sk', pa.int32()),
                ('wp_web_page_id', pa.string()),
                ('wp_rec_start_date', pa.date32()),
                ('wp_rec_end_date', pa.date32()),
                ('wp_creation_date_sk', pa.int32()),
                ('wp_access_date_sk', pa.int32()),
                ('wp_autogen_flag', pa.string()),
                ('wp_customer_sk', pa.int32()),
                ('wp_url', pa.string()),
                ('wp_type', pa.string()),
                ('wp_char_count', pa.int32()),
                ('wp_link_count', pa.int32()),
                ('wp_image_count', pa.int32()),
                ('wp_max_ad_count', pa.int32())
            ]),
            'warehouse': pa.schema([
                ('w_warehouse_sk', pa.int32()),
                ('w_warehouse_id', pa.string()),
                ('w_warehouse_name', pa.string()),
                ('w_warehouse_sq_ft', pa.int32()),
                ('w_street_number', pa.string()),
                ('w_street_name', pa.string()),
                ('w_street_type', pa.string()),
                ('w_suite_number', pa.string()),
                ('w_city', pa.string()),
                ('w_county', pa.string()),
                ('w_state', pa.string()),
                ('w_zip', pa.string()),
                ('w_country', pa.string()),
                ('w_gmt_offset', pa.decimal128(5, 2))
            ]),
            'customer': pa.schema([
                ('c_customer_sk', pa.int32()),
                ('c_customer_id', pa.string()),
                ('c_current_cdemo_sk', pa.int32()),
                ('c_current_hdemo_sk', pa.int32()),
                ('c_current_addr_sk', pa.int32()),
                ('c_first_shipto_date_sk', pa.int32()),
                ('c_first_sales_date_sk', pa.int32()),
                ('c_salutation', pa.string()),
                ('c_first_name', pa.string()),
                ('c_last_name', pa.string()),
                ('c_preferred_cust_flag', pa.string()),
                ('c_birth_day', pa.int32()),
                ('c_birth_month', pa.int32()),
                ('c_birth_year', pa.int32()),
                ('c_birth_country', pa.string()),
                ('c_login', pa.string()),
                ('c_email_address', pa.string()),
                ('c_last_review_date', pa.string())
            ]),
            'customer_address': pa.schema([
                ('ca_address_sk', pa.int32()),
                ('ca_address_id', pa.string()),
                ('ca_street_number', pa.string()),
                ('ca_street_name', pa.string()),
                ('ca_street_type', pa.string()),
                ('ca_suite_number', pa.string()),
                ('ca_city', pa.string()),
                ('ca_county', pa.string()),
                ('ca_state', pa.string()),
                ('ca_zip', pa.string()),
                ('ca_country', pa.string()),
                ('ca_gmt_offset', pa.decimal128(5, 2)),
                ('ca_location_type', pa.string())
            ]),
            'customer_demographics': pa.schema([
                ('cd_demo_sk', pa.int32()),
                ('cd_gender', pa.string()),
                ('cd_marital_status', pa.string()),
                ('cd_education_status', pa.string()),
                ('cd_purchase_estimate', pa.int32()),
                ('cd_credit_rating', pa.string()),
                ('cd_dep_count', pa.int32()),
                ('cd_dep_employed_count', pa.int32()),
                ('cd_dep_college_count', pa.int32())
            ]),
            'date_dim': pa.schema([
                ('d_date_sk', pa.int32()),
                ('d_date_id', pa.string()),
                ('d_date', pa.date32()),
                ('d_month_seq', pa.int32()),
                ('d_week_seq', pa.int32()),
                ('d_quarter_seq', pa.int32()),
                ('d_year', pa.int32()),
                ('d_dow', pa.int32()),
                ('d_moy', pa.int32()),
                ('d_dom', pa.int32()),
                ('d_qoy', pa.int32()),
                ('d_fy_year', pa.int32()),
                ('d_fy_quarter_seq', pa.int32()),
                ('d_fy_week_seq', pa.int32()),
                ('d_day_name', pa.string()),
                ('d_quarter_name', pa.string()),
                ('d_holiday', pa.string()),
                ('d_weekend', pa.string()),
                ('d_following_holiday', pa.string()),
                ('d_first_dom', pa.int32()),
                ('d_last_dom', pa.int32()),
                ('d_same_day_ly', pa.int32()),
                ('d_same_day_lq', pa.int32()),
                ('d_current_day', pa.string()),
                ('d_current_week', pa.string()),
                ('d_current_month', pa.string()),
                ('d_current_quarter', pa.string()),
                ('d_current_year', pa.string())
            ]),
            'household_demographics': pa.schema([
                ('hd_demo_sk', pa.int32()),
                ('hd_income_band_sk', pa.int32()),
                ('hd_buy_potential', pa.string()),
                ('hd_dep_count', pa.int32()),
                ('hd_vehicle_count', pa.int32())
            ]),
            'item': pa.schema([
                ('i_item_sk', pa.int32()),
                ('i_item_id', pa.string()),
                ('i_rec_start_date', pa.date32()),
                ('i_rec_end_date', pa.date32()),
                ('i_item_desc', pa.string()),
                ('i_current_price', pa.decimal128(7, 2)),
                ('i_wholesale_cost', pa.decimal128(7, 2)),
                ('i_brand_id', pa.int32()),
                ('i_brand', pa.string()),
                ('i_class_id', pa.int32()),
                ('i_class', pa.string()),
                ('i_category_id', pa.int32()),
                ('i_category', pa.string()),
                ('i_manufact_id', pa.int32()),
                ('i_manufact', pa.string()),
                ('i_size', pa.string()),
                ('i_formulation', pa.string()),
                ('i_color', pa.string()),
                ('i_units', pa.string()),
                ('i_container', pa.string()),
                ('i_manager_id', pa.int32()),
                ('i_product_name', pa.string())
            ]),
            'income_band': pa.schema([
                ('ib_income_band_sk', pa.int32()),
                ('ib_lower_bound', pa.int32()),
                ('ib_upper_bound', pa.int32())
            ]),
            'promotion': pa.schema([
                ('p_promo_sk', pa.int32()),
                ('p_promo_id', pa.string()),
                ('p_start_date_sk', pa.int32()),
                ('p_end_date_sk', pa.int32()),
                ('p_item_sk', pa.int32()),
                ('p_cost', pa.decimal128(15, 2)),
                ('p_response_target', pa.int32()),
                ('p_promo_name', pa.string()),
                ('p_channel_dmail', pa.string()),
                ('p_channel_email', pa.string()),
                ('p_channel_catalog', pa.string()),
                ('p_channel_tv', pa.string()),
                ('p_channel_radio', pa.string()),
                ('p_channel_press', pa.string()),
                ('p_channel_event', pa.string()),
                ('p_channel_demo', pa.string()),
                ('p_channel_details', pa.string()),
                ('p_purpose', pa.string()),
                ('p_discount_active', pa.string())
            ]),
            'reason': pa.schema([
                ('r_reason_sk', pa.int32()),
                ('r_reason_id', pa.string()),
                ('r_reason_desc', pa.string())
            ]),
            'ship_mode': pa.schema([
                ('sm_ship_mode_sk', pa.int32()),
                ('sm_ship_mode_id', pa.string()),
                ('sm_type', pa.string()),
                ('sm_code', pa.string()),
                ('sm_carrier', pa.string()),
                ('sm_contract', pa.string())
            ]),
            'time_dim': pa.schema([
                ('t_time_sk', pa.int32()),
                ('t_time_id', pa.string()),
                ('t_time', pa.int32()),
                ('t_hour', pa.int32()),
                ('t_minute', pa.int32()),
                ('t_second', pa.int32()),
                ('t_am_pm', pa.string()),
                ('t_shift', pa.string()),
                ('t_sub_shift', pa.string()),
                ('t_meal_time', pa.string())
            ])
        }
        
        if table_name not in schemas:
            raise KeyError(
                f"Unknown TPC-DS table: {table_name}. "
                f"Valid tables: {', '.join(sorted(schemas.keys()))}"
            )
        
        return schemas[table_name]


class SchemaFactory:
    """
    Factory for creating dataset schema instances.
    
    This provides a centralized way to instantiate the correct schema
    implementation based on the benchmark type.
    """
    
    _SCHEMAS: Dict[BenchmarkType, type[DatasetSchema]] = {
        BenchmarkType.TPCH: TPCHSchema,
        BenchmarkType.TPCDS: TPCDSSchema,
    }
    
    @classmethod
    def create(cls, benchmark_type: BenchmarkType) -> DatasetSchema:
        """
        Create a schema instance for the given benchmark type.
        
        Args:
            benchmark_type: The type of benchmark
            
        Returns:
            DatasetSchema instance for the benchmark
            
        Raises:
            ValueError: If benchmark_type is not supported
        """
        if benchmark_type not in cls._SCHEMAS:
            raise ValueError(
                f"Unsupported benchmark type: {benchmark_type}. "
                f"Supported types: {list(cls._SCHEMAS.keys())}"
            )
        
        schema_class = cls._SCHEMAS[benchmark_type]
        return schema_class()
    
    @classmethod
    def register(cls, benchmark_type: BenchmarkType, 
                 schema_class: type[DatasetSchema]) -> None:
        """
        Register a new schema type (for extensibility).
        
        Args:
            benchmark_type: The benchmark type identifier
            schema_class: The DatasetSchema implementation class
        """
        cls._SCHEMAS[benchmark_type] = schema_class
        logger.info(f"Registered schema for benchmark type: {benchmark_type.value}")
