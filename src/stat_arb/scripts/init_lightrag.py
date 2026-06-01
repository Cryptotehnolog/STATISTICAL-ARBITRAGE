"""Initialize LightRAG with embedded vector store.

This script sets up LightRAG for the first time, creating necessary
directories and verifying the configuration.

Usage:
    uv run python -m stat_arb.scripts.init_lightrag
"""

import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from stat_arb.memory.config import LightRAGConfig
from stat_arb.memory.lightrag_client import LightRAGClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

console = Console()


def init_lightrag() -> int:
    """Initialize LightRAG with embedded vector store.
    
    Returns:
        Exit code (0 for success, 1 for failure).
    """
    try:
        console.print("\n[bold blue]Initializing LightRAG...[/bold blue]\n")
        
        # Load configuration
        config = LightRAGConfig()
        
        # Display configuration
        config_table = Table(title="LightRAG Configuration")
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="green")
        
        config_table.add_row("Vector Store", config.vector_store)
        config_table.add_row("Embedding Model", config.embedding_model)
        config_table.add_row("Embedding Dimensions", str(config.embedding_dim))
        config_table.add_row("Chunk Size", f"{config.chunk_size} tokens")
        config_table.add_row("Chunk Overlap", f"{config.chunk_overlap} tokens")
        config_table.add_row("Storage Path", str(config.storage_path))
        config_table.add_row("Vector Store Path", str(config.vector_store_path))
        config_table.add_row("Batch Size", str(config.batch_size))
        config_table.add_row("Max Workers", str(config.max_workers))
        
        console.print(config_table)
        console.print()
        
        # Create directories
        console.print("[yellow]Creating storage directories...[/yellow]")
        config.ensure_directories()
        console.print(f"✓ Created {config.storage_path}")
        console.print(f"✓ Created {config.vector_store_path}")
        console.print()
        
        # Initialize client
        console.print("[yellow]Initializing LightRAG client...[/yellow]")
        client = LightRAGClient(config)
        console.print("✓ LightRAG client initialized")
        console.print()
        
        # Load embedding model
        console.print("[yellow]Loading embedding model...[/yellow]")
        console.print(f"  Model: {config.embedding_model}")
        console.print("  This may take a moment on first run...")
        _ = client.embedding_model  # Trigger lazy loading
        console.print("✓ Embedding model loaded")
        console.print()
        
        # Run health check
        console.print("[yellow]Running health check...[/yellow]")
        health = client.health_check()
        
        health_table = Table(title="Health Check Results")
        health_table.add_column("Check", style="cyan")
        health_table.add_column("Status", style="green")
        
        for key, value in health.items():
            if key == "status":
                status_color = "green" if value == "healthy" else "red"
                health_table.add_row(
                    key.replace("_", " ").title(),
                    f"[{status_color}]{value}[/{status_color}]",
                )
            else:
                health_table.add_row(
                    key.replace("_", " ").title(),
                    str(value),
                )
        
        console.print(health_table)
        console.print()
        
        # Insert test document
        console.print("[yellow]Inserting test document...[/yellow]")
        test_text = """
This is a test document to verify LightRAG initialization.

LightRAG provides long-term memory and knowledge graph capabilities
for the multi-agent quantitative research system. It stores:
- Hypothesis rationale and source references
- Statistical test summaries
- Backtest conclusions and lessons learned
- Critic objections and detected risks
- Architecture decisions and rationales
- Agent lessons learned
- Manual notes and human decisions

The system uses embedded vector stores (FAISS or Chroma) to minimize
infrastructure requirements for the MVP.
"""
        client.insert(test_text, metadata={"type": "test", "purpose": "initialization"})
        console.print("✓ Test document inserted")
        console.print()
        
        # Test query
        console.print("[yellow]Testing query functionality...[/yellow]")
        result = client.query("What does LightRAG store?", mode="hybrid", top_k=1)
        console.print(f"✓ Query successful")
        console.print(f"\n[dim]Query result preview:[/dim]")
        console.print(Panel(result[:200] + "..." if len(result) > 200 else result))
        console.print()
        
        # Success message
        console.print(
            Panel.fit(
                "[bold green]✓ LightRAG initialization complete![/bold green]\n\n"
                "The system is ready to store and retrieve:\n"
                "  • Agent decisions and rationale\n"
                "  • Development knowledge\n"
                "  • Research insights\n"
                "  • Architecture decisions\n\n"
                f"Storage location: {config.storage_path}\n"
                f"Vector store: {config.vector_store_path}",
                title="Success",
                border_style="green",
            )
        )
        
        return 0
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Initialization failed:[/bold red] {e}\n")
        logger.exception("LightRAG initialization failed")
        return 1


def main() -> None:
    """Main entry point."""
    sys.exit(init_lightrag())


if __name__ == "__main__":
    main()
