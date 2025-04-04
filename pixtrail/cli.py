"""
Command-line interface for the PixTrail package.
"""

import argparse
import os
import sys
from typing import List, Optional

from .core import PixTrail
from .utils import ensure_directory, get_default_output_path


def parse_args(args: List[str] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Args:
        args: Command-line arguments (if None, use sys.argv)
        
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Extract GPS data from photos and create GPX files"
    )
    
    # Create a group for input arguments
    input_group = parser.add_mutually_exclusive_group()
    
    input_group.add_argument(
        "-i", "--input-dir",
        help="Directory containing photos with GPS data"
    )
    
    input_group.add_argument(
        "-b", "--batch",
        nargs='+',
        help="Process multiple directories (batch mode)"
    )
    
    input_group.add_argument(
        "-w", "--web",
        action="store_true",
        help="Start the web interface"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output GPX file path (default: auto-named in the input directory)"
    )
    
    parser.add_argument(
        "-d", "--output-dir",
        help="Output directory for batch mode (default: each input directory)"
    )
    
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Search for images recursively in subdirectories"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    # Web interface options
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for the web interface (default: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port for the web interface (default: 5000)"
    )
    
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't automatically open a browser when starting the web interface"
    )
    
    # Require at least one mode (input dir, batch, or web)
    if args is None:
        args = sys.argv[1:]
    
    if not args or (
        not any(arg in args for arg in ['-i', '--input-dir', '-b', '--batch', '-w', '--web'])
    ):
        if not args:
            return parser.parse_args(['-h'])
        else:
            parser.error("One of -i/--input-dir, -b/--batch, or -w/--web is required")
    
    return parser.parse_args(args)


def main(args: List[str] = None) -> int:
    """
    Main entry point for the command-line interface.
    
    Args:
        args: Command-line arguments (if None, use sys.argv)
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Parse arguments
    parsed_args = parse_args(args)
    
    # Check which mode to use
    if parsed_args.web:
        return start_web_interface(parsed_args)
    elif parsed_args.batch:
        return process_batch(PixTrail(), parsed_args)
    elif parsed_args.input_dir:
        return process_single(PixTrail(), parsed_args)
    else:
        print("Error: No operation mode specified")
        return 1


def start_web_interface(args: argparse.Namespace) -> int:
    """
    Start the web interface.
    
    Args:
        args: Parsed arguments
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Import web server module here to avoid dependency issues if not needed
        from .web import start_server
        
        print(f"Starting PixTrail web interface on http://{args.host}:{args.port}")
        app, server = start_server(
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser
        )
        
        # Keep the server running
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down server...")
            server.shutdown()
            print("Server stopped")
        
        return 0
    
    except ImportError:
        print("Error: Web interface dependencies not installed")
        print("Install with: pip install pixtrail[web]")
        return 1
    
    except Exception as e:
        print(f"Error starting web interface: {e}")
        return 1


def process_single(pixtrail: PixTrail, args: argparse.Namespace) -> int:
    """
    Process a single directory and generate a GPX file.
    
    Args:
        pixtrail: PixTrail object
        args: Parsed arguments
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    input_dir = args.input_dir
    
    # Check if input directory exists
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory does not exist: {input_dir}")
        return 1
    
    # Set output path
    output_path = args.output
    
    # If output path is provided, ensure its directory exists
    if output_path:
        output_dir = os.path.dirname(os.path.abspath(output_path))
        if not ensure_directory(output_dir):
            print(f"Error: Could not create output directory: {output_dir}")
            return 1
    
    try:
        # Process and generate GPX file
        if args.verbose:
            print(f"Processing images in {input_dir}")
            if args.recursive:
                print("Searching recursively in subdirectories")
        
        success = pixtrail.process_and_generate(
            input_dir,
            output_path,
            args.recursive
        )
        
        if success:
            # Get the actual output path for display
            actual_output = output_path if output_path else get_default_output_path(input_dir)
            print(f"GPX file created successfully: {actual_output}")
            return 0
        else:
            print("Failed to create GPX file")
            return 1
    
    except Exception as e:
        print(f"Error: {e}")
        return 1


def process_batch(pixtrail: PixTrail, args: argparse.Namespace) -> int:
    """
    Process multiple directories and generate GPX files for each.
    
    Args:
        pixtrail: PixTrail object
        args: Parsed arguments
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Check each input directory
    valid_dirs = []
    for dir_path in args.batch:
        if os.path.isdir(dir_path):
            valid_dirs.append(dir_path)
        else:
            print(f"Warning: Skipping non-existent directory: {dir_path}")
    
    if not valid_dirs:
        print("Error: No valid directories to process")
        return 1
    
    # Process each directory
    success_count = 0
    fail_count = 0
    
    for dir_path in valid_dirs:
        try:
            if args.verbose:
                print(f"\nProcessing directory: {dir_path}")
                if args.recursive:
                    print("Searching recursively in subdirectories")
            
            # Determine output path for this directory
            if args.output_dir:
                # If output directory is specified, use it with auto-naming
                dir_name = os.path.basename(os.path.normpath(dir_path))
                # Clean directory name for use in filename
                dir_name = ''.join(c for c in dir_name if c.isalnum() or c in (' ', '_', '-'))
                dir_name = dir_name.strip()
                if not dir_name:
                    dir_name = "PixTrail"
                output_path = os.path.join(args.output_dir, f"{dir_name}.gpx")
                
                # Ensure output directory exists
                if not ensure_directory(args.output_dir):
                    print(f"Error: Could not create output directory: {args.output_dir}")
                    fail_count += 1
                    continue
            else:
                # Use auto-naming in the input directory
                output_path = None
            
            # Process and generate GPX file
            success = pixtrail.process_and_generate(
                dir_path,
                output_path,
                args.recursive
            )
            
            if success:
                # Get the actual output path for display
                actual_output = output_path if output_path else get_default_output_path(dir_path)
                print(f"GPX file created successfully: {actual_output}")
                success_count += 1
            else:
                print(f"Failed to create GPX file for directory: {dir_path}")
                fail_count += 1
        
        except Exception as e:
            print(f"Error processing directory {dir_path}: {e}")
            fail_count += 1
    
    # Print summary
    print(f"\nBatch processing completed: {success_count} succeeded, {fail_count} failed")
    
    # Return success if at least one directory was processed successfully
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
