"""
Detectors package for static analysis
"""
import importlib
import inspect
import os
import sys
import logging
from typing import List, Type
from pathlib import Path

from stylus_analyzer.detectors.detector_base import BaseDetector
from stylus_analyzer.detectors.unchecked_transfer import UncheckedTransferDetector
from stylus_analyzer.detectors.unwrap_detector import UnwrapDetector
from stylus_analyzer.detectors.panic_detector import PanicDetector
from stylus_analyzer.detectors.encode_packed_detector import EncodePackedDetector
from stylus_analyzer.detectors.locked_ether_detector import LockedEtherDetector

# Logger for this module
logger = logging.getLogger(__name__)

# List of all available detectors
AVAILABLE_DETECTORS = [
    UncheckedTransferDetector,
    UnwrapDetector,
    PanicDetector,
    EncodePackedDetector,
    LockedEtherDetector
]

def get_available_detectors() -> List[Type[BaseDetector]]:
    """
    Gets all available detectors, both built-in and dynamically discovered
    
    Returns:
        List of detector classes
    """
    return AVAILABLE_DETECTORS

def register_detector(detector_class: Type[BaseDetector]) -> None:
    """
    Register a new detector class
    
    Args:
        detector_class: The detector class to register
    """
    if detector_class not in AVAILABLE_DETECTORS:
        AVAILABLE_DETECTORS.append(detector_class)
        logger.info(f"Registered detector: {detector_class.__name__}")

def load_detectors_from_path(path: str) -> None:
    """
    Load detector classes from a specified path
    
    Args:
        path: Path to a directory containing detector modules
    """
    detector_path = Path(path)
    if not detector_path.exists() or not detector_path.is_dir():
        logger.warning(f"Detector path {path} does not exist or is not a directory")
        return
    
    # Add the path to sys.path if it's not already there
    if str(detector_path.parent) not in sys.path:
        sys.path.append(str(detector_path.parent))
    
    # Iterate through Python files in the directory
    for file_path in detector_path.glob("*.py"):
        if file_path.name.startswith("_"):
            continue
        
        module_name = file_path.stem
        try:
            # Import the module
            module = importlib.import_module(f"{detector_path.name}.{module_name}")
            
            # Find detector classes in the module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseDetector) and 
                    obj != BaseDetector):
                    register_detector(obj)
                    
        except (ImportError, AttributeError) as e:
            logger.warning(f"Error loading detector from {file_path}: {str(e)}") 
