"""
Iceberg metadata collection.

Collects snapshot IDs, manifest counts, and other Iceberg-specific metadata.
"""

import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class IcebergMetadataCollector:
    """Collects Iceberg-specific metadata from tables."""
    
    @staticmethod
    def collect_metadata(
        cursor,
        catalog: str,
        schema: str,
        tables: List[str]
    ) -> Dict[str, Any]:
        """
        Collect Iceberg-specific metadata for loaded tables.
        
        Args:
            cursor: Database cursor
            catalog: Iceberg catalog name
            schema: Schema name
            tables: List of table names
        
        Returns:
            Dict with Iceberg metadata:
                - snapshot_ids: Dict[table_name, snapshot_id]
                - snapshot_timestamps: Dict[table_name, timestamp]
                - manifest_counts: Dict[table_name, count]
                - format_version: Iceberg format version
                - storage_location: Storage base location
        """
        snapshot_ids = {}
        snapshot_timestamps = {}
        manifest_counts = {}
        format_version = None
        storage_location = None
        
        for table_name in tables:
            try:
                # Get current snapshot information
                snapshot_query = f"""
                    SELECT snapshot_id, committed_at
                    FROM "{catalog}"."{schema}"."{table_name}$snapshots"
                    ORDER BY committed_at DESC
                    LIMIT 1
                """
                cursor.execute(snapshot_query)
                snapshot_row = cursor.fetchone()
                
                if snapshot_row:
                    snapshot_ids[table_name] = snapshot_row[0]
                    snapshot_timestamps[table_name] = str(snapshot_row[1])
                
                # Get manifest count from files table
                files_query = f"""
                    SELECT COUNT(DISTINCT manifest_file)
                    FROM "{catalog}"."{schema}"."{table_name}$files"
                """
                cursor.execute(files_query)
                manifest_row = cursor.fetchone()
                
                if manifest_row and manifest_row[0]:
                    manifest_counts[table_name] = manifest_row[0]
                
                # Get table properties (format version, location) - only once
                if format_version is None or storage_location is None:
                    try:
                        props_query = f"SHOW CREATE TABLE {table_name}"
                        cursor.execute(props_query)
                        create_stmt = cursor.fetchone()
                        
                        if create_stmt:
                            stmt_text = create_stmt[0]
                            # Extract format version from CREATE TABLE statement
                            if 'format_version' in stmt_text.lower():
                                # Parse format version from properties
                                match = re.search(r"format_version\s*=\s*['\"]?(\d+)", stmt_text, re.IGNORECASE)
                                if match:
                                    format_version = int(match.group(1))
                            
                            # Extract location
                            if 'location' in stmt_text.lower():
                                match = re.search(r"location\s*=\s*['\"]([^'\"]+)", stmt_text, re.IGNORECASE)
                                if match:
                                    loc = match.group(1)
                                    # Get base location (remove table-specific path)
                                    if '/' + table_name in loc:
                                        storage_location = loc.split('/' + table_name)[0]
                                    else:
                                        storage_location = loc
                    except Exception as e:
                        logger.debug(f"Could not extract table properties: {e}")
                
            except Exception as e:
                logger.debug(f"Could not collect metadata for {table_name}: {e}")
        
        # Default format version if not detected
        if format_version is None:
            format_version = 2  # Iceberg v2 is default in modern systems
        
        return {
            'snapshot_ids': snapshot_ids,
            'snapshot_timestamps': snapshot_timestamps,
            'manifest_counts': manifest_counts,
            'format_version': format_version,
            'storage_location': storage_location
        }
