"""
Help information display for CLI commands.
"""
import sys
import textwrap
from typing import Optional, Dict, List, Tuple

from osyllabi.utils.cli.cmd_desc import COMMAND_DESC

from osyllabi.utils.log import log


def display_header() -> None:
    """Display the application header."""
    from osyllabi import __version__
    
    print(f"\nOsyllabi - A Python-powered curriculum designer")
    print(f"Version: {__version__}\n")
    print("Generates personalized curriculums using AI, web crawling, and data integration.\n")


def get_command_usage_info(command_name: str) -> Tuple[str, Dict[str, str], List[str]]:
    """
    Get usage info for a specific command.
    
    Args:
        command_name: Name of the command
        
    Returns:
        Tuple containing usage string, options dict, and examples list
    """
    # Default usage pattern
    usage = f"Usage: osyllabi {command_name}"
    options = {
        "--debug": "Enable debug mode for detailed logging and error information"
    }
    examples = []
    
    if command_name == "create":
        usage += " TOPIC [options]"
        options.update({
            "TOPIC": "Main topic or subject for the curriculum (required)",
            "--title, -t": "Custom title for the curriculum (default: '<topic> Curriculum')",
            "--level, -s": "Target skill level (Beginner, Intermediate, Advanced, Expert, Master, Pioneer)",
            "--links, -l": "URLs to include as resources",
            "--source": "Source files or directories to include\nDefault: current directory",
            "--export-path, -o": "Directory to export the curriculum",
            "--format, -f": "Output format (md, pdf, html, docx, json)",
            "--help, -h": "Display this help message"
        })
        examples = [
            'osyllabi create "Machine Learning" --title "ML Fundamentals" --level Beginner',
            'osyllabi create "Python Programming" --links "https://docs.python.org" --format pdf',
            'osyllabi create "Web Development" -t "Full Stack Web Dev" -s Advanced',
            'osyllabi create "Data Science" --format json',
            'osyllabi create "Machine Learning" --level Master --title "Advanced Neural Models"'
        ]
    elif command_name == "clean":
        usage += " [options]"
        options.update({
            "--output-dir": "Clean specific output directory",
            "--all, -a": "Clean all generated files",
            "--cache": "Clean only cached files",
            "--force, -f": "Force clean without confirmation",
            "--help, -h": "Display this help message"
        })
        examples = [
            'osyllabi clean --all',
            'osyllabi clean --output-dir "./output" --force',
            'osyllabi clean --all --debug'
        ]
    elif command_name == "help":
        usage += " [command]"
        options.update({
            "command": "Command to get help for",
            "--help, -h": "Display this help message"
        })
        examples = [
            'osyllabi help',
            'osyllabi help create',
            'osyllabi help --debug'
        ]
    
    return usage, options, examples


def display_command_help(command_name: str, command_descriptions: Dict[str, str]) -> None:
    """
    Display help for a specific command.
    
    Args:
        command_name: Name of the command to display help for
        command_descriptions: Dictionary of command names to their descriptions
    """
    if command_name not in command_descriptions:
        display_help_for_unknown_command(command_name)
        return
        
    log.debug(f"Displaying help for command: {command_name}")
    display_header()
        
    description = command_descriptions[command_name]
    usage, options, examples = get_command_usage_info(command_name)
    
    print(f"\nOSYLLABI {command_name.upper()}")
    print(f"\n{description}\n")
    print(usage)
    
    if options:
        print("\nOptions:" if not command_name == "help" else "\nArguments:")
        max_opt_len = max(len(opt) for opt in options.keys())
        for opt, desc in options.items():
            desc_lines = desc.split('\n')
            print(f"  {opt.ljust(max_opt_len)}    {desc_lines[0]}")
            for line in desc_lines[1:]:
                print(f"  {' ' * max_opt_len}    {line}")
    
    if examples:
        print("\nExamples:")
        for example in examples:
            print(f"  {example}")


def display_general_help(command_descriptions: Dict[str, str]) -> None:
    """Display general help for all commands."""
    log.debug("Displaying general help")
    display_header()
    
    print("Usage: osyllabi [options] COMMAND [command-options]")
    
    print("\nCommands:")
    max_len = max(len(name) for name in command_descriptions.keys())
    for cmd_name, description in sorted(command_descriptions.items()):
        print(f"  {cmd_name.ljust(max_len)}    {description}")
    
    print("\nGlobal Options:")
    print("  --help, -h         Display help for a command")
    print("  --debug            Enable debug mode for detailed logging and error information")
    
    print("\nRun 'osyllabi <command> --help' for more information on a specific command.")


def display_epilog() -> None:
    """Display epilog information after help text."""
    epilog = textwrap.dedent("""\
        For more information and examples, visit:
        https://github.com/p3nGu1nZz/osyllabi
        
        Report issues at:
        https://github.com/p3nGu1nZz/osyllabi/issues
    """)
    print("\n" + epilog)


def display_help_for_unknown_command(attempted_command: str) -> None:
    """Display help message for an unknown command."""
    log.warning(f"Unknown command requested: '{attempted_command}'")


def show_help(command: Optional[str] = None) -> None:
    """
    Display help information for commands.
    
    Args:
        command: Specific command to show help for, or None for general help
    """
    if command:
        display_command_help(command, COMMAND_DESC)
    else:
        display_general_help(COMMAND_DESC)
    
    display_epilog()


def is_help_requested(args_list: Optional[List[str]] = None) -> bool:
    """
    Check if help is requested based on command line arguments.
    
    Args:
        args_list: List of command line arguments, uses sys.argv if None
        
    Returns:
        bool: True if help is requested, False otherwise
    """
    if args_list is None:
        args_list = sys.argv[1:]
        
    return '-h' in args_list or '--help' in args_list or 'help' in args_list
