"""
Quick test script for Phase 1
Run this to verify the setup is working correctly.
"""

import asyncio
import sys

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


async def test_health():
    """Test basic health endpoint"""
    console.print("\n[bold cyan]Testing Health Endpoint...[/bold cyan]")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                console.print("[green]✓[/green] Health endpoint working")
                return True
            else:
                console.print(f"[red]✗[/red] Health endpoint returned {response.status_code}")
                return False
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to connect: {e}")
        console.print("[yellow]Make sure the server is running: python main.py[/yellow]")
        return False


async def test_llm_health():
    """Test LLM health endpoint"""
    console.print("\n[bold cyan]Testing LLM Health...[/bold cyan]")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/scenarios/health")
            data = response.json()
            
            if data.get("status") == "healthy":
                console.print(f"[green]✓[/green] Ollama is running")
                console.print(f"[green]✓[/green] Model '{data.get('model')}' is available")
                return True
            else:
                console.print(f"[yellow]⚠[/yellow] {data.get('message')}")
                return False
    except Exception as e:
        console.print(f"[red]✗[/red] LLM health check failed: {e}")
        return False


async def test_scenario_generation():
    """Test scenario generation"""
    console.print("\n[bold cyan]Testing Scenario Generation...[/bold cyan]")
    
    test_prompt = "What happens if fusion energy becomes viable in 2030?"
    console.print(f"Prompt: [italic]{test_prompt}[/italic]")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating scenarios...", total=None)
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "http://localhost:8000/api/scenarios/generate",
                    json={"prompt": test_prompt, "num_scenarios": 3},
                )
                
                progress.update(task, completed=True)
        
        if response.status_code == 200:
            data = response.json()
            scenarios = data.get("scenarios", [])
            
            console.print(f"\n[green]✓[/green] Generated {len(scenarios)} scenarios")
            
            # Display scenarios
            for i, scenario in enumerate(scenarios, 1):
                panel_content = f"""[bold]{scenario['title']}[/bold]
                
Category: {scenario['category']}
Probability: {scenario['probability']}

{scenario['description']}

Timeline Events: {len(scenario['timeline'])}"""
                
                console.print(
                    Panel(
                        panel_content,
                        title=f"Scenario {i}",
                        border_style="cyan",
                    )
                )
            
            return True
        else:
            console.print(f"[red]✗[/red] Generation failed with status {response.status_code}")
            console.print(response.text)
            return False
            
    except Exception as e:
        console.print(f"[red]✗[/red] Scenario generation failed: {e}")
        return False


async def run_tests():
    """Run all tests"""
    console.print(
        Panel.fit(
            "[bold cyan]AetherMind Phase 1 Test Suite[/bold cyan]",
            border_style="cyan",
        )
    )
    
    results = []
    
    # Test 1: Health
    results.append(await test_health())
    
    # Test 2: LLM Health
    if results[-1]:
        results.append(await test_llm_health())
    else:
        console.print("\n[yellow]Skipping remaining tests (server not running)[/yellow]")
        return False
    
    # Test 3: Scenario Generation
    if results[-1]:
        results.append(await test_scenario_generation())
    else:
        console.print("\n[yellow]Skipping scenario generation test (LLM not ready)[/yellow]")
        return False
    
    # Summary
    console.print("\n" + "=" * 60)
    if all(results):
        console.print(
            Panel.fit(
                "[bold green]✓ All tests passed! Phase 1 is working correctly.[/bold green]",
                border_style="green",
            )
        )
        return True
    else:
        console.print(
            Panel.fit(
                "[bold red]✗ Some tests failed. Check the output above.[/bold red]",
                border_style="red",
            )
        )
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(run_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrupted by user[/yellow]")
        sys.exit(1)
