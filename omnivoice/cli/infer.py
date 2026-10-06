"""Single-item inference CLI for OmniVoice.

Generates audio from a single text input using voice cloning,
voice design, or auto voice.

Usage:
    # Voice cloning
    omnivoice-infer --model k2-fsa/OmniVoice \
        --text "Hello, this is a text for text-to-speech." \
        --ref_audio ref.wav --ref_text "Reference transcript." --output out.wav

    # Voice design
    omnivoice-infer --model k2-fsa/OmniVoice \
        --text "Hello, this is a text for text-to-speech." \
        --instruct "male, British accent" --output out.wav

    # Auto voice
    omnivoice-infer --model k2-fsa/OmniVoice \
        --text "Hello, this is a text for text-to-speech." --output out.wav
"""

import argparse
import logging

import torch

from omnivoice.cli.audio_output import resolve_audio_output_path
from omnivoice.models.omnivoice import OmniVoice
from omnivoice.service.audio import OUTPUT_FORMATS, write_encoded_audio_file
from omnivoice.utils.common import str2bool


def get_best_device():
    """Auto-detect the best available device: CUDA > MPS > CPU."""
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="OmniVoice single-item inference",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--model",
        type=str,
        default="k2-fsa/OmniVoice",
        help="Model checkpoint path or HuggingFace repo id.",
    )
    parser.add_argument(
        "--text",
        type=str,
        required=True,
        help="Text to synthesize.",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output audio path. The extension selects the format unless --format is set.",
    )
    parser.add_argument(
        "--format",
        "--output_format",
        dest="output_format",
        choices=sorted(OUTPUT_FORMATS),
        default=None,
        help="Output format. When set, the output extension is adjusted to match.",
    )
    # Voice cloning
    parser.add_argument(
        "--ref_audio",
        type=str,
        default=None,
        help="Reference audio file path for voice cloning.",
    )
    parser.add_argument(
        "--ref_text",
        type=str,
        default=None,
        help="Reference text describing the reference audio.",
    )
    # Voice design
    parser.add_argument(
        "--instruct",
        type=str,
        default=None,
        help="Style instruction for voice design mode.",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language name (e.g. 'English') or code (e.g. 'en').",
    )
    # Generation parameters
    parser.add_argument("--num_step", type=int, default=32)
    parser.add_argument("--guidance_scale", type=float, default=2.0)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument(
        "--normalize_text",
        type=str2bool,
        default=False,
        help="Normalize supported English structured text before synthesis.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Audio-token budget expressed in seconds. Overrides speed, but "
        "the decoded waveform length may vary slightly.",
    )
    parser.add_argument("--t_shift", type=float, default=0.1)
    parser.add_argument("--denoise", type=str2bool, default=True)
    parser.add_argument(
        "--postprocess_output",
        type=str2bool,
        default=True,
    )
    parser.add_argument(
        "--pad_duration",
        type=float,
        default=0.1,
        help="Silence padding duration per side in seconds. Set to 0 to disable.",
    )
    parser.add_argument(
        "--fade_duration",
        type=float,
        default=0.1,
        help="Fade-in/out curve duration in seconds. Set to 0 to disable.",
    )
    parser.add_argument("--float_preserving_silence", type=str2bool, default=True)
    parser.add_argument("--output_min_silence_ms", type=int, default=500)
    parser.add_argument("--output_keep_silence_ms", type=int, default=1000)
    parser.add_argument("--output_lead_silence_ms", type=int, default=100)
    parser.add_argument("--output_trail_silence_ms", type=int, default=100)
    parser.add_argument("--output_preserve_active_edges", type=str2bool, default=False)
    parser.add_argument(
        "--output_peak_limit",
        type=float,
        default=None,
        help="Optional absolute peak ceiling in the range (0, 1].",
    )
    parser.add_argument("--layer_penalty_factor", type=float, default=5.0)
    parser.add_argument("--position_temperature", type=float, default=5.0)
    parser.add_argument("--class_temperature", type=float, default=0.0)
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Device to use for inference. Auto-detected if not specified.",
    )
    return parser


def main():
    formatter = "%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s"
    logging.basicConfig(format=formatter, level=logging.INFO, force=True)

    args = get_parser().parse_args()

    device = args.device or get_best_device()
    logging.info(f"Loading model from {args.model} on {device} ...")
    model = OmniVoice.from_pretrained(
        args.model, device_map=device, dtype=torch.float16
    )

    logging.info(f"Generating audio for: {args.text[:80]}...")
    audios = model.generate(
        text=args.text,
        language=args.language,
        ref_audio=args.ref_audio,
        ref_text=args.ref_text,
        instruct=args.instruct,
        duration=args.duration,
        num_step=args.num_step,
        guidance_scale=args.guidance_scale,
        speed=args.speed,
        normalize_text=args.normalize_text,
        t_shift=args.t_shift,
        denoise=args.denoise,
        postprocess_output=args.postprocess_output,
        pad_duration=args.pad_duration,
        fade_duration=args.fade_duration,
        float_preserving_silence=args.float_preserving_silence,
        output_min_silence_ms=args.output_min_silence_ms,
        output_keep_silence_ms=args.output_keep_silence_ms,
        output_lead_silence_ms=args.output_lead_silence_ms,
        output_trail_silence_ms=args.output_trail_silence_ms,
        output_preserve_active_edges=args.output_preserve_active_edges,
        output_peak_limit=args.output_peak_limit,
        layer_penalty_factor=args.layer_penalty_factor,
        position_temperature=args.position_temperature,
        class_temperature=args.class_temperature,
    )

    output_path, output_format = resolve_audio_output_path(args.output, args.output_format)
    write_encoded_audio_file(
        audios[0],
        output_path,
        output_format,
        model.sampling_rate,
    )
    logging.info(f"Saved {output_format.upper()} to {output_path}")


if __name__ == "__main__":
    main()
