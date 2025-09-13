"""
Personal Voice MVLM Manager

Manages interchangeable MVLM models for personal voice generation.
Supports both MVLM-GPT2 and Enhanced SIM-ONE for benchmarking and optimization.
"""

import os
import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig

from mcg_agent.config import get_settings
from mcg_agent.utils.exceptions import MVLMError, ModelLoadError
from mcg_agent.utils.audit import AuditLogger


class MVLMModelType(str, Enum):
    """Available MVLM model types"""
    MVLM_GPT2 = "mvlm_gpt2"
    SIMONE_ENHANCED = "simone_enhanced"


class VoiceContext(BaseModel):
    """Context for voice-aware text generation"""
    voice_patterns: List[str] = Field(description="Voice patterns to apply")
    tone: str = Field(description="Desired tone (casual, professional, etc.)")
    audience: str = Field(description="Target audience")
    context_type: str = Field(description="Type of context (email, social, article, etc.)")
    corpus_sources: List[str] = Field(description="Source corpora for voice patterns")
    influence_level: float = Field(description="0-1 level of voice influence desired")


class VoiceGenerationRequest(BaseModel):
    """Request for voice-aware text generation"""
    prompt: str = Field(description="Base prompt for generation")
    voice_context: VoiceContext = Field(description="Voice context to apply")
    max_length: int = Field(default=512, description="Maximum generation length")
    temperature: float = Field(default=0.7, description="Generation temperature")
    top_p: float = Field(default=0.9, description="Top-p sampling")
    model_type: MVLMModelType = Field(default=MVLMModelType.MVLM_GPT2)


class VoiceGenerationResult(BaseModel):
    """Result of voice-aware text generation"""
    generated_text: str = Field(description="Generated text")
    model_used: MVLMModelType = Field(description="Model that generated the text")
    generation_time_ms: float = Field(description="Time taken for generation")
    voice_consistency_score: float = Field(description="0-1 score of voice consistency")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VoiceBenchmarkResults(BaseModel):
    """Results of voice quality benchmarking between models"""
    test_prompts_count: int = Field(description="Number of test prompts used")
    mvlm_gpt2_results: Dict[str, float] = Field(description="MVLM-GPT2 performance metrics")
    simone_enhanced_results: Dict[str, float] = Field(description="Enhanced SIM-ONE performance metrics")
    comparison_summary: Dict[str, Any] = Field(description="Comparative analysis")
    recommendation: str = Field(description="Recommended model for voice replication")


class ModelPerformanceMetrics(BaseModel):
    """Performance metrics for a model"""
    average_generation_time_ms: float
    voice_consistency_score: float
    output_quality_score: float
    memory_usage_mb: float
    tokens_per_second: float


class PersonalVoiceMVLMManager:
    """
    Manage MVLM models for personal voice generation.
    
    Supports interchangeable models for benchmarking:
    - MVLM-GPT2: Traditional GPT-2 architecture with biblical worldview optimization
    - Enhanced SIM-ONE: Modern transformer with governance mechanisms
    
    Provides voice-aware text generation that maintains user's authentic voice.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.audit_logger = AuditLogger()
        self.models: Dict[MVLMModelType, Dict[str, Any]] = {}
        self.tokenizers: Dict[MVLMModelType, Any] = {}
        self.active_model = MVLMModelType.MVLM_GPT2
        self._performance_metrics: Dict[MVLMModelType, List[ModelPerformanceMetrics]] = {
            MVLMModelType.MVLM_GPT2: [],
            MVLMModelType.SIMONE_ENHANCED: []
        }
        self._initialize_models()
        
    def _initialize_models(self) -> None:
        """Initialize available MVLM models"""
        try:
            # Check for available models
            mvlm_gpt2_path = Path(self.settings.MVLM_GPT2_MODEL_PATH)
            simone_enhanced_path = Path(self.settings.SIMONE_ENHANCED_MODEL_PATH)
            
            if mvlm_gpt2_path.exists():
                self._load_mvlm_gpt2()
            else:
                self.audit_logger.log_warning(f"MVLM-GPT2 model not found at {mvlm_gpt2_path}")
                
            if simone_enhanced_path.exists():
                self._load_enhanced_simone()
            else:
                self.audit_logger.log_warning(f"Enhanced SIM-ONE model not found at {simone_enhanced_path}")
                
            if not self.models:
                raise ModelLoadError("No MVLM models available")
                
        except Exception as e:
            raise ModelLoadError(f"Failed to initialize MVLM models: {str(e)}")
            
    def _load_mvlm_gpt2(self) -> None:
        """Load MVLM-GPT2 model"""
        try:
            model_path = self.settings.MVLM_GPT2_MODEL_PATH
            
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
                
            # Load model
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            
            # Configure generation
            generation_config = GenerationConfig(
                max_length=512,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
            
            self.models[MVLMModelType.MVLM_GPT2] = {
                "model": model,
                "generation_config": generation_config,
                "loaded_at": datetime.utcnow(),
                "model_path": model_path
            }
            
            self.tokenizers[MVLMModelType.MVLM_GPT2] = tokenizer
            
            self.audit_logger.log_info(f"MVLM-GPT2 model loaded from {model_path}")
            
        except Exception as e:
            raise ModelLoadError(f"Failed to load MVLM-GPT2: {str(e)}")
            
    def _load_enhanced_simone(self) -> None:
        """Load Enhanced SIM-ONE model"""
        try:
            model_path = self.settings.SIMONE_ENHANCED_MODEL_PATH
            
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
                
            # Load model
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            
            # Configure generation with SIM-ONE specific settings
            generation_config = GenerationConfig(
                max_length=512,
                temperature=0.6,  # Slightly lower for more consistent governance
                top_p=0.85,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
            
            self.models[MVLMModelType.SIMONE_ENHANCED] = {
                "model": model,
                "generation_config": generation_config,
                "loaded_at": datetime.utcnow(),
                "model_path": model_path
            }
            
            self.tokenizers[MVLMModelType.SIMONE_ENHANCED] = tokenizer
            
            self.audit_logger.log_info(f"Enhanced SIM-ONE model loaded from {model_path}")
            
        except Exception as e:
            raise ModelLoadError(f"Failed to load Enhanced SIM-ONE: {str(e)}")
            
    def switch_model(self, model_type: MVLMModelType) -> bool:
        """
        Switch active model for benchmarking.
        
        Args:
            model_type: Model type to switch to
            
        Returns:
            bool: True if switch successful
        """
        try:
            if model_type not in self.models:
                raise MVLMError(f"Model {model_type} not available")
                
            old_model = self.active_model
            self.active_model = model_type
            
            self.audit_logger.log_info(f"Switched active model from {old_model} to {model_type}")
            
            return True
            
        except Exception as e:
            self.audit_logger.log_error(f"Failed to switch model to {model_type}: {str(e)}")
            return False
            
    def craft_voice_prompt(self, user_query: str, voice_context: VoiceContext) -> str:
        """
        Create prompts that include user's voice patterns.
        
        Args:
            user_query: Original user query
            voice_context: Voice context to apply
            
        Returns:
            str: Voice-enhanced prompt
        """
        try:
            # Build voice-aware prompt
            voice_prompt_parts = []
            
            # Add voice pattern context
            if voice_context.voice_patterns:
                voice_patterns_text = " ".join(voice_context.voice_patterns[:5])  # Limit to top 5
                voice_prompt_parts.append(f"Voice patterns: {voice_patterns_text}")
                
            # Add tone and audience context
            voice_prompt_parts.append(f"Tone: {voice_context.tone}")
            voice_prompt_parts.append(f"Audience: {voice_context.audience}")
            voice_prompt_parts.append(f"Context: {voice_context.context_type}")
            
            # Combine with user query
            voice_context_str = " | ".join(voice_prompt_parts)
            voice_prompt = f"[{voice_context_str}]\n\nQuery: {user_query}\n\nResponse:"
            
            return voice_prompt
            
        except Exception as e:
            self.audit_logger.log_error(f"Failed to craft voice prompt: {str(e)}")
            return user_query  # Fallback to original query
            
    async def generate_with_voice(
        self, 
        request: VoiceGenerationRequest
    ) -> VoiceGenerationResult:
        """
        Generate text that matches user's voice patterns.
        
        Args:
            request: Voice generation request
            
        Returns:
            VoiceGenerationResult: Generated text with voice consistency
        """
        try:
            start_time = time.time()
            
            # Use specified model or active model
            model_type = request.model_type if request.model_type in self.models else self.active_model
            
            if model_type not in self.models:
                raise MVLMError(f"Model {model_type} not available")
                
            model_info = self.models[model_type]
            tokenizer = self.tokenizers[model_type]
            
            # Craft voice-aware prompt
            voice_prompt = self.craft_voice_prompt(request.prompt, request.voice_context)
            
            # Tokenize input
            inputs = tokenizer.encode(voice_prompt, return_tensors="pt")
            
            # Move to appropriate device
            device = next(model_info["model"].parameters()).device
            inputs = inputs.to(device)
            
            # Generate text
            with torch.no_grad():
                generation_config = model_info["generation_config"]
                generation_config.max_length = min(request.max_length, 1024)
                generation_config.temperature = request.temperature
                generation_config.top_p = request.top_p
                
                outputs = model_info["model"].generate(
                    inputs,
                    generation_config=generation_config,
                    pad_token_id=tokenizer.eos_token_id
                )
                
            # Decode output
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract only the generated part (remove prompt)
            if voice_prompt in generated_text:
                generated_text = generated_text.replace(voice_prompt, "").strip()
                
            generation_time_ms = (time.time() - start_time) * 1000
            
            # Calculate voice consistency score (simplified)
            voice_consistency_score = self._calculate_voice_consistency(
                generated_text, 
                request.voice_context
            )
            
            result = VoiceGenerationResult(
                generated_text=generated_text,
                model_used=model_type,
                generation_time_ms=generation_time_ms,
                voice_consistency_score=voice_consistency_score,
                metadata={
                    "prompt_length": len(voice_prompt),
                    "output_length": len(generated_text),
                    "temperature": request.temperature,
                    "top_p": request.top_p
                }
            )
            
            # Record performance metrics
            self._record_performance_metrics(model_type, result, inputs.shape[1])
            
            self.audit_logger.log_info(
                f"Generated text with {model_type}: {len(generated_text)} chars in {generation_time_ms:.1f}ms"
            )
            
            return result
            
        except Exception as e:
            raise MVLMError(f"Failed to generate with voice: {str(e)}")
            
    def _calculate_voice_consistency(self, text: str, voice_context: VoiceContext) -> float:
        """
        Calculate voice consistency score (simplified implementation).
        
        Args:
            text: Generated text
            voice_context: Voice context used
            
        Returns:
            float: Voice consistency score (0-1)
        """
        try:
            score = 0.0
            checks = 0
            
            # Check for voice pattern presence
            if voice_context.voice_patterns:
                pattern_matches = sum(1 for pattern in voice_context.voice_patterns if pattern.lower() in text.lower())
                score += (pattern_matches / len(voice_context.voice_patterns)) * 0.4
                checks += 1
                
            # Check tone appropriateness (simplified)
            tone_keywords = {
                "professional": ["therefore", "furthermore", "however", "consequently"],
                "casual": ["yeah", "really", "pretty", "kind of"],
                "formal": ["moreover", "nevertheless", "accordingly", "subsequently"]
            }
            
            if voice_context.tone in tone_keywords:
                tone_matches = sum(1 for keyword in tone_keywords[voice_context.tone] if keyword in text.lower())
                score += min(tone_matches / len(tone_keywords[voice_context.tone]), 1.0) * 0.3
                checks += 1
                
            # Check length appropriateness
            if 50 <= len(text) <= 500:  # Reasonable length
                score += 0.3
                checks += 1
                
            return score / max(checks, 1)
            
        except Exception:
            return 0.5  # Default moderate score
            
    def _record_performance_metrics(
        self, 
        model_type: MVLMModelType, 
        result: VoiceGenerationResult,
        input_tokens: int
    ) -> None:
        """Record performance metrics for benchmarking"""
        try:
            tokens_per_second = input_tokens / (result.generation_time_ms / 1000) if result.generation_time_ms > 0 else 0
            
            metrics = ModelPerformanceMetrics(
                average_generation_time_ms=result.generation_time_ms,
                voice_consistency_score=result.voice_consistency_score,
                output_quality_score=0.8,  # Placeholder - would need more sophisticated scoring
                memory_usage_mb=0.0,  # Placeholder - would need actual memory monitoring
                tokens_per_second=tokens_per_second
            )
            
            self._performance_metrics[model_type].append(metrics)
            
            # Keep only recent metrics (last 100)
            if len(self._performance_metrics[model_type]) > 100:
                self._performance_metrics[model_type] = self._performance_metrics[model_type][-100:]
                
        except Exception as e:
            self.audit_logger.log_error(f"Failed to record performance metrics: {str(e)}")
            
    async def benchmark_voice_quality(self, test_prompts: List[str]) -> VoiceBenchmarkResults:
        """
        Compare voice replication quality between models.
        
        Args:
            test_prompts: List of test prompts for benchmarking
            
        Returns:
            VoiceBenchmarkResults: Comparative analysis
        """
        try:
            if len(self.models) < 2:
                raise MVLMError("Need at least 2 models for benchmarking")
                
            results = {}
            
            # Test each available model
            for model_type in self.models.keys():
                model_results = []
                
                for prompt in test_prompts:
                    # Create test voice context
                    voice_context = VoiceContext(
                        voice_patterns=["authentic", "natural", "consistent"],
                        tone="professional",
                        audience="general",
                        context_type="test",
                        corpus_sources=["personal"],
                        influence_level=0.7
                    )
                    
                    request = VoiceGenerationRequest(
                        prompt=prompt,
                        voice_context=voice_context,
                        model_type=model_type
                    )
                    
                    result = await self.generate_with_voice(request)
                    model_results.append(result)
                    
                # Calculate aggregate metrics
                avg_time = sum(r.generation_time_ms for r in model_results) / len(model_results)
                avg_consistency = sum(r.voice_consistency_score for r in model_results) / len(model_results)
                
                results[model_type] = {
                    "average_generation_time_ms": avg_time,
                    "average_voice_consistency": avg_consistency,
                    "total_tests": len(model_results)
                }
                
            # Create comparison
            mvlm_gpt2_results = results.get(MVLMModelType.MVLM_GPT2, {})
            simone_enhanced_results = results.get(MVLMModelType.SIMONE_ENHANCED, {})
            
            # Determine recommendation
            recommendation = "mvlm_gpt2"  # Default
            if simone_enhanced_results and mvlm_gpt2_results:
                if (simone_enhanced_results.get("average_voice_consistency", 0) > 
                    mvlm_gpt2_results.get("average_voice_consistency", 0)):
                    recommendation = "simone_enhanced"
                    
            comparison_summary = {
                "speed_winner": min(results.keys(), key=lambda k: results[k].get("average_generation_time_ms", float('inf'))),
                "quality_winner": max(results.keys(), key=lambda k: results[k].get("average_voice_consistency", 0)),
                "overall_recommendation": recommendation
            }
            
            benchmark_results = VoiceBenchmarkResults(
                test_prompts_count=len(test_prompts),
                mvlm_gpt2_results=mvlm_gpt2_results,
                simone_enhanced_results=simone_enhanced_results,
                comparison_summary=comparison_summary,
                recommendation=recommendation
            )
            
            self.audit_logger.log_info(f"Completed voice quality benchmark with {len(test_prompts)} prompts")
            
            return benchmark_results
            
        except Exception as e:
            raise MVLMError(f"Failed to benchmark voice quality: {str(e)}")
            
    def get_model_status(self) -> Dict[str, Any]:
        """Get status of all loaded models"""
        status = {
            "active_model": self.active_model,
            "available_models": list(self.models.keys()),
            "model_info": {}
        }
        
        for model_type, model_info in self.models.items():
            status["model_info"][model_type] = {
                "loaded_at": model_info["loaded_at"].isoformat(),
                "model_path": str(model_info["model_path"]),
                "performance_samples": len(self._performance_metrics[model_type])
            }
            
        return status


__all__ = [
    "PersonalVoiceMVLMManager",
    "VoiceGenerationRequest",
    "VoiceGenerationResult", 
    "VoiceContext",
    "VoiceBenchmarkResults",
    "MVLMModelType"
]
