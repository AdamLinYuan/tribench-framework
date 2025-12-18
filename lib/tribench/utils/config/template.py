"""
Configuration template generation.

Generates system configuration files from HOCON using Jinja2 templates.
"""

from pathlib import Path
from typing import Optional
from pyhocon import ConfigTree
from jinja2 import Environment, FileSystemLoader, Template
import logging

from .loader import ConfigurationError

logger = logging.getLogger(__name__)


class ConfigurationTemplate:
    """
    Template-based system configuration generator.
    
    Generates system-specific configuration files (e.g., Trino's config.properties)
    from HOCON configuration using Jinja2 templates.
    """
    
    def __init__(self, templates_path: Optional[Path] = None):
        """
        Initialize the template generator.
        
        Args:
            templates_path: Path to template directory.
                          If None, use config/templates/
        """
        if templates_path is None:
            root_path = Path(__file__).parent.parent.parent.parent.parent
            templates_path = root_path / "config" / "templates"
        
        self.templates_path = Path(templates_path)
        
        if self.templates_path.exists():
            self.env = Environment(
                loader=FileSystemLoader(str(self.templates_path)),
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True
            )
        else:
            logger.warning(f"Templates directory not found: {self.templates_path}")
            self.env = None
    
    def generate(self, 
                template_name: str, 
                config: ConfigTree, 
                output_path: Optional[Path] = None,
                **kwargs) -> str:
        """
        Generate configuration file from template.
        
        Args:
            template_name: Name of the template file
            config: Configuration data
            output_path: Optional path to write generated config
            **kwargs: Additional variables to pass to the template
        
        Returns:
            Generated configuration as string
        
        Raises:
            ConfigurationError: If template not found or rendering fails
        """
        if self.env is None:
            raise ConfigurationError(
                f"Templates directory not found: {self.templates_path}"
            )
        
        try:
            template = self.env.get_template(template_name)
            rendered = template.render(config=config, **kwargs)
            
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(rendered)
                logger.info(f"Generated config file: {output_path}")
            
            return rendered
            
        except Exception as e:
            raise ConfigurationError(
                f"Failed to generate config from template {template_name}: {e}"
            ) from e
    
    def generate_from_string(self, 
                            template_str: str, 
                            config: ConfigTree,
                            output_path: Optional[Path] = None) -> str:
        """
        Generate configuration from template string.
        
        Args:
            template_str: Template string
            config: Configuration data
            output_path: Optional path to write generated config
        
        Returns:
            Generated configuration as string
        """
        try:
            template = Template(template_str)
            rendered = template.render(config=config)
            
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(rendered)
                logger.info(f"Generated config file: {output_path}")
            
            return rendered
            
        except Exception as e:
            raise ConfigurationError(
                f"Failed to generate config from template string: {e}"
            ) from e
