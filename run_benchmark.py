#!/usr/bin/env python3
"""
FenBench: Chess Visual Understanding Benchmark Runner

This script runs the complete FenBench evaluation, loading tasks and images,
sending them to an LLM with JSON schema enforcement, and evaluating results.

Author: Claude Code
"""

import os
import json
import base64
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# ============================================================================
# CONFIGURATION - MODIFY THESE SETTINGS
# ============================================================================

# Name of the model
MODEL_NAME = "gpt-4o"

# Maximum number of tasks to run (None for all tasks)
MAX_TASKS = None  # Set to a number like 10 for testing, None for full benchmark

# Starting task number (1-200)
START_TASK = 1  # Set to a number like 50 to start from task 50

# ============================================================================
# MODIFIABLE LLM PROVIDER SECTION - CUSTOMIZE THIS FOR YOUR LLM
# ============================================================================
#Example Setup using OpenAI API
def setup_llm_client():
    """
    Setup your LLM client here
    """
    try:
        from openai import OpenAI
        import os
        
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
	if not api_key:
    		raise RuntimeError("OPENAI_API_KEY is not set")
		
	client = OpenAI(api_key=api_key)
        return client
    except ImportError:
        print("ERROR: OpenAI library not installed. Run: pip install openai")
        print("Or modify the setup_llm_client() function to use your preferred LLM provider.")
        return None

def call_llm_with_schema(client, image_path: str, system_prompt: str, user_prompt: str, 
                         schema: Dict[str, Any], model: str) -> Optional[Dict[str, Any]]:
    """
    Call the LLM with image and enforce JSON schema response.
    
    MODIFY THIS FUNCTION to work with your LLM provider.
    
    Args:
        client: LLM client instance
        image_path: Path to the image file
        system_prompt: System prompt text
        user_prompt: User question/prompt
        schema: JSON schema to enforce
        model: Model name to use
    
    Returns:
        Dict containing the parsed JSON response, or None if failed
    """
    try:
        # Read and encode image
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Prepare messages
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}"
                        }
                    }
                ]
            }
        ]
        
        # Call OpenAI API with structured output
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "chess_analysis",
                    "strict": True, 
                    "schema": schema
                }
            }
        )
        
        # Parse response
        response_text = response.choices[0].message.content
        return json.loads(response_text)
        
    except Exception as e:
        print(f"ERROR calling LLM: {e}")
        return None

# ============================================================================
# END MODIFIABLE SECTION
# ============================================================================


class FenBenchRunner:
    """Main benchmark runner class."""
    
    def __init__(self, model_name: str):
        self.data_dir = Path("data")
        self.model_name = model_name
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)
        
        # Load schemas
        self.schemas = self._load_schemas()
        
        # Load system prompts
        self.system_prompts = self._load_system_prompts()
        
        # Initialize results
        self.results = {
            "benchmark_info": {
                "start_time": datetime.now().isoformat(),
                "total_tasks": 0,
                "completed_tasks": 0,
                "categories": {
                    "1": {"name": "Piece Identification", "total": 0, "correct": 0},
                    "2": {"name": "Square Location", "total": 0, "correct": 0}, 
                    "3": {"name": "Piece Counting", "total": 0, "correct": 0},
                    "4": {"name": "FEN Generation", "total": 0, "correct": 0}
                }
            },
            "task_results": []
        }
    
    def _load_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Load JSON schemas for each category."""
        schemas = {}
        schema_dir = self.data_dir / "schemas"
        
        for i in range(1, 5):
            schema_file = schema_dir / f"category_{i}_schema.json"
            with open(schema_file, 'r') as f:
                schemas[str(i)] = json.load(f)
            print(f"✓ Loaded schema for category {i}")
                
        return schemas
    
    def _load_system_prompts(self) -> Dict[str, str]:
        """Load system prompts."""
        prompts = {}
        prompt_dir = self.data_dir / "system_prompt"
        
        # Load base prompt
        with open(prompt_dir / "system_prompt_base.txt", 'r') as f:
            base_prompt = f.read().strip()
        print("✓ Loaded base system prompt")
            
        # Load end prompt
        with open(prompt_dir / "system_prompt_end.txt", 'r') as f:
            end_prompt = f.read().strip()
        print("✓ Loaded end system prompt")
            
        # Load category-specific prompts
        for i in range(1, 5):
            with open(prompt_dir / f"system_prompt_type{i}.txt", 'r') as f:
                category_prompt = f.read().strip()
            prompts[str(i)] = f"{base_prompt}\n\n{category_prompt}\n\n{end_prompt}"
            print(f"✓ Loaded system prompt for category {i}")
                
        return prompts
    
    def _load_tasks(self, start_task: int = 1) -> List[Dict[str, Any]]:
        """Load task files starting from specified task number."""
        tasks = []
        task_dir = self.data_dir / "tasks"
        
        # Load tasks in order starting from start_task
        for i in range(start_task, 201):
            task_file = task_dir / f"task{i:03d}.json"
            with open(task_file, 'r') as f:
                task = json.load(f)
                tasks.append(task)
                
        print(f"✓ Loaded {len(tasks)} tasks (starting from task {start_task})")
        return tasks
    
    def _evaluate_response(self, task: Dict[str, Any], response: Dict[str, Any]) -> bool:
        """Evaluate if the LLM response matches expected answer."""
        category = task["category"]
        expected = task["expected_answer"]
        
        try:
            if category == "1":
                # Piece identification - exact match
                return response.get("piece") == expected
                
            elif category == "2":
                # Square location - compare sorted lists
                response_squares = sorted(response.get("squares", []))
                expected_squares = sorted(expected)
                return response_squares == expected_squares
                
            elif category == "3":
                # Piece counting - filter out zero counts and compare dictionaries
                response_counts = response.get("piece_counts", {})
                # Remove pieces with 0 count to match expected format
                filtered_counts = {piece: count for piece, count in response_counts.items() if count > 0}
                return filtered_counts == expected
                
            elif category == "4":
                # FEN generation - exact match
                return response.get("fen") == expected
                
        except Exception as e:
            print(f"ERROR evaluating response: {e}")
            return False
            
        return False
    
    def _save_results(self, filename: str):
        """Save current results to JSON file."""
        results_file = self.results_dir / filename
        
        # Update completion info
        self.results["benchmark_info"]["end_time"] = datetime.now().isoformat()
        self.results["benchmark_info"]["completed_tasks"] = len(self.results["task_results"])
        
        # Calculate accuracy per category
        for category_id, category_info in self.results["benchmark_info"]["categories"].items():
            if category_info["total"] > 0:
                category_info["accuracy"] = category_info["correct"] / category_info["total"]
            else:
                category_info["accuracy"] = 0.0
        
        # Calculate overall accuracy
        total_correct = sum(cat["correct"] for cat in self.results["benchmark_info"]["categories"].values())
        total_tasks = sum(cat["total"] for cat in self.results["benchmark_info"]["categories"].values())
        self.results["benchmark_info"]["overall_accuracy"] = total_correct / total_tasks if total_tasks > 0 else 0.0
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"✓ Results saved to {results_file}")
    
    def run_benchmark(self, model: str, max_tasks: Optional[int] = None, start_task: int = 1):
        """Run the complete benchmark."""
        print("=" * 60)
        print("🏁 Starting FenBench Evaluation")
        print("=" * 60)
        
        # Setup LLM client
        print("🔧 Setting up LLM client...")
        client = setup_llm_client()
        if client is None:
            print("❌ Failed to setup LLM client. Exiting.")
            return
        
        # Load tasks
        print("📁 Loading tasks...")
        tasks = self._load_tasks(start_task)
        if not tasks:
            print("❌ No tasks loaded. Exiting.")
            return
            
        # Apply max_tasks limit if specified
        if max_tasks and max_tasks < len(tasks):
            tasks = tasks[:max_tasks]
            print(f"🔢 Limited to first {max_tasks} tasks")
        
        self.results["benchmark_info"]["total_tasks"] = len(tasks)
        
        # Count tasks per category
        for task in tasks:
            category = task["category"]
            self.results["benchmark_info"]["categories"][category]["total"] += 1
        
        print(f"📊 Total tasks: {len(tasks)}")
        for cat_id, cat_info in self.results["benchmark_info"]["categories"].items():
            if cat_info["total"] > 0:
                print(f"   Category {cat_id} ({cat_info['name']}): {cat_info['total']} tasks")
        
        print("\n🚀 Starting evaluation...")
        print("-" * 60)
        
        # Process each task
        for i, task in enumerate(tasks, 1):
            task_id = task["test_id"]
            category = task["category"]
            
            print(f"[{i:3d}/{len(tasks)}] Task {task_id} (Category {category})", end=" - ")
            
            try:
                # Construct image path
                image_filename = f"task{int(task_id):03d}.png"
                image_path = self.data_dir / "images" / image_filename
                
                if not image_path.exists():
                    print(f"❌ Image not found: {image_path}")
                    continue
                
                # Get system prompt and schema for this category
                system_prompt = self.system_prompts.get(category, "")
                schema = self.schemas.get(category, {})
                
                # Construct user prompt with orientation info
                orientation_info = f"Red corner: {task['orientation']['red_corner']}, Blue corner: {task['orientation']['blue_corner']}"
                user_prompt = f"Board orientation - {orientation_info}\n\nQuestion: {task['question']}"
                
                # Call LLM
                response = call_llm_with_schema(
                    client=client,
                    image_path=str(image_path),
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=schema,
                    model=model
                )
                
                if response is None:
                    print("❌ LLM call failed")
                    task_result = {
                        "task_id": task_id,
                        "category": category,
                        "question": task["question"],
                        "expected_answer": task["expected_answer"],
                        "llm_response": None,
                        "correct": False,
                        "error": "LLM call failed"
                    }
                else:
                    # Evaluate response
                    is_correct = self._evaluate_response(task, response)
                    
                    if is_correct:
                        print("✅ Correct")
                        self.results["benchmark_info"]["categories"][category]["correct"] += 1
                    else:
                        print("❌ Incorrect")
                    
                    task_result = {
                        "task_id": task_id,
                        "category": category,
                        "question": task["question"],
                        "expected_answer": task["expected_answer"],
                        "llm_response": response,
                        "correct": is_correct,
                        "error": None
                    }
                
                self.results["task_results"].append(task_result)
                
                # Save progress every 10 tasks
                if i % 10 == 0:
                    model_safe = self.model_name.replace('/', '_').replace('-', '_')
                    self._save_results(f"fenbench_progress_{model_safe}.json")
                    print(f"💾 Progress saved ({i}/{len(tasks)} completed)")
                
            except KeyboardInterrupt:
                print("\n⚠️ Benchmark interrupted by user")
                model_safe = self.model_name.replace('/', '_').replace('-', '_')
                self._save_results(f"fenbench_interrupted_{model_safe}.json")
                return
                
            except Exception as e:
                print(f"❌ Error: {e}")
                task_result = {
                    "task_id": task_id,
                    "category": category,
                    "question": task.get("question", ""),
                    "expected_answer": task.get("expected_answer", ""),
                    "llm_response": None,
                    "correct": False,
                    "error": str(e)
                }
                self.results["task_results"].append(task_result)
        
        print("\n" + "=" * 60)
        print("🏁 Benchmark Complete!")
        print("=" * 60)
        
        # Print final results
        self._print_summary()
        
        # Rename progress file to final results
        model_safe = self.model_name.replace('/', '_').replace('-', '_')
        progress_file = self.results_dir / f"fenbench_progress_{model_safe}.json"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_file = self.results_dir / f"fenbench_results_{model_safe}_{timestamp}.json"
        
        # Save final version then rename
        self._save_results(f"fenbench_progress_{model_safe}.json")
        progress_file.rename(final_file)
        print(f"📝 Renamed progress file to {final_file.name}")
    
    def _print_summary(self):
        """Print benchmark summary."""
        categories = self.results["benchmark_info"]["categories"]
        
        print(f"📊 FINAL RESULTS:")
        print(f"   Total tasks: {self.results['benchmark_info']['total_tasks']}")
        print(f"   Completed: {len(self.results['task_results'])}")
        
        total_correct = 0
        total_attempted = 0
        
        for cat_id, cat_info in categories.items():
            if cat_info["total"] > 0:
                accuracy = cat_info["correct"] / cat_info["total"] * 100
                print(f"   Category {cat_id} ({cat_info['name']}): {cat_info['correct']}/{cat_info['total']} ({accuracy:.1f}%)")
                total_correct += cat_info["correct"]
                total_attempted += cat_info["total"]
        
        if total_attempted > 0:
            overall_accuracy = total_correct / total_attempted * 100
            print(f"   Overall Accuracy: {total_correct}/{total_attempted} ({overall_accuracy:.1f}%)")


def main():
    print(f"🤖 Model: {MODEL_NAME}")
    print(f"📁 Data directory: data")
    print(f"🏁 Start task: {START_TASK}")
    print(f"🔢 Max tasks: {MAX_TASKS if MAX_TASKS else 'All remaining tasks'}")
    print()
    
    # Create benchmark runner
    runner = FenBenchRunner(model_name=MODEL_NAME)
    
    # Run benchmark
    runner.run_benchmark(model=MODEL_NAME, max_tasks=MAX_TASKS, start_task=START_TASK)


if __name__ == "__main__":
    main()