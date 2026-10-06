from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
from ssml_h import SSMLPlan as SharedSSMLPlan

from omnivoice.service.ssml import (
    DEFAULT_DYNAMIC_VOICE_SAMPLE_LANGUAGE,
    DEFAULT_DYNAMIC_VOICE_SAMPLE_TEXT,
    MAX_BREAK_MS,
    MAX_SSML_NESTING,
    SSML_H_NAMESPACE,
    SSMLValidationError,
    compile_ssml,
    ssml_capabilities,
)
from omnivoice.service.ssml_execution import (
    IMPLICIT_HANDOFF_MS,
    SSMLExecutionSession,
    SSMLVoiceBinding,
)


def resolve_language(value: str) -> str:
    aliases = {
        "en-US": "en",
        "en-GB": "en",
        "pl-PL": "pl",
        "English": "en",
        "Polish": "pl",
    }
    if value in {"en", "pl"}:
        return value
    if value not in aliases:
        raise ValueError(f"Unsupported language '{value}'.")
    return aliases[value]


class SSMLParserTests(unittest.TestCase):
    def test_standard_controls_compile_in_document_order(self) -> None:
        plan = compile_ssml(
            """<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
              Hello <sub alias="World Wide Web Consortium">W3C</sub>.
              <break time="500ms"/>
              Attempt <say-as interpret-as="ordinal">3</say-as> by
              <say-as interpret-as="characters">API</say-as>.
            </speak>""",
            "ssml",
            resolve_language=resolve_language,
        )

        self.assertEqual([unit.kind for unit in plan.units], ["speech", "break", "speech"])
        self.assertIn("World Wide Web Consortium", plan.units[0].text)
        self.assertEqual(plan.units[1].duration_ms, 500)
        self.assertIn("3rd", plan.units[2].text)
        self.assertIn("A P I", plan.units[2].text)
        self.assertIsInstance(plan, SharedSSMLPlan)

    def test_ssml_h_voice_definition_and_standard_turns(self) -> None:
        plan = compile_ssml(
            f"""<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis"
                xmlns:h="{SSML_H_NAMESPACE}" xml:lang="en-US">
              <metadata><h:extensions version="1.0">
                <h:voice-definition name="Bob" gender="male" age="elderly"
                  accent="american" scope="profile" replace="true" seed="42">
                  <h:sample xml:lang="en-US">My name is Bob.</h:sample>
                </h:voice-definition>
              </h:extensions></metadata>
              <voice name="Bob" required="name">Are we ready?</voice>
            </speak>""",
            "ssml-h",
            resolve_language=resolve_language,
        )

        definition = plan.voice_definitions[0]
        self.assertEqual(definition.name, "Bob")
        self.assertEqual(definition.scope, "profile")
        self.assertTrue(definition.replace)
        self.assertEqual(definition.seed, 42)
        self.assertEqual(definition.sample, "My name is Bob.")
        self.assertEqual(plan.units[0].voice, "Bob")

    def test_ssml_h_metadata_requires_explicit_mode(self) -> None:
        document = f"""<speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:h="{SSML_H_NAMESPACE}">
          <metadata><h:extensions version="1.0"><h:voice-definition name="Bob" gender="male"/></h:extensions></metadata>
          Hello.
        </speak>"""
        with self.assertRaisesRegex(SSMLValidationError, "input_type='ssml-h'"):
            compile_ssml(document, "ssml")

    def test_ssml_h_metadata_does_not_ignore_stray_text(self) -> None:
        document = f"""<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:h="{SSML_H_NAMESPACE}">
          <metadata><h:extensions version="1.0"><h:voice-definition name="Bob" gender="male">
            <h:sample>Hello.</h:sample> stray
          </h:voice-definition></h:extensions></metadata><voice name="Bob">Hello.</voice>
        </speak>"""
        with self.assertRaisesRegex(SSMLValidationError, "metadata text"):
            compile_ssml(document, "ssml-h")

    def test_voice_language_and_nested_prosody_are_inherited(self) -> None:
        plan = compile_ssml(
            """<speak version="1.1" xml:lang="en-US">
              Root.
              <voice name="roxyvoice"><lang xml:lang="pl-PL">Cześć.</lang></voice>
              <prosody rate="80%" pitch="+2st" volume="-3dB">
                Styled <prosody rate="125%" pitch="-1st">nested.</prosody>
              </prosody>
            </speak>""",
            "ssml",
            resolve_language=resolve_language,
            validate_voice=lambda name, _definitions: None if name == "roxyvoice" else (_ for _ in ()).throw(ValueError("missing")),
        )

        polish = next(unit for unit in plan.units if "Cześć" in unit.text)
        nested = next(unit for unit in plan.units if "nested" in unit.text)
        self.assertEqual((polish.language, polish.voice), ("pl", "roxyvoice"))
        self.assertAlmostEqual(nested.prosody.rate, 1.0)
        self.assertAlmostEqual(nested.prosody.pitch_semitones, 1.0)

    def test_break_strength_and_explicit_zero_are_preserved(self) -> None:
        plan = compile_ssml(
            '<speak>Hello.<break strength="weak"/><break time="0ms"/>Now.</speak>',
            "ssml",
        )
        breaks = [unit.duration_ms for unit in plan.units if unit.kind == "break"]
        self.assertEqual(breaks, [200, 0])

    def test_arpabet_is_bounded_and_english_only(self) -> None:
        plan = compile_ssml(
            '<speak xml:lang="en-US">I will <phoneme alphabet="x-arpabet" ph="R EH1 D">read</phoneme>.</speak>',
            "ssml",
            resolve_language=resolve_language,
        )
        self.assertIn("[R EH1 D]", plan.units[0].text)
        with self.assertRaisesRegex(SSMLValidationError, "generic IPA"):
            compile_ssml(
                '<speak xml:lang="en-US"><phoneme alphabet="ipa" ph="wɜːld">world</phoneme></speak>',
                "ssml",
                resolve_language=resolve_language,
            )
        with self.assertRaisesRegex(SSMLValidationError, "English"):
            compile_ssml(
                '<speak xml:lang="pl-PL"><phoneme alphabet="x-arpabet" ph="R EH1 D">read</phoneme></speak>',
                "ssml",
                resolve_language=resolve_language,
            )

    def test_unknown_voice_tag_attribute_and_namespace_are_rejected(self) -> None:
        with self.assertRaisesRegex(SSMLValidationError, "not available"):
            compile_ssml(
                '<speak><voice name="missing">No.</voice></speak>',
                "ssml",
                validate_voice=lambda name, _definitions: (_ for _ in ()).throw(ValueError(f"Voice '{name}' is not available.")),
            )
        with self.assertRaisesRegex(SSMLValidationError, "Unsupported attribute"):
            compile_ssml('<speak><prosody contour="bad">No.</prosody></speak>', "ssml")
        with self.assertRaisesRegex(SSMLValidationError, "Unsupported synthesis namespace"):
            compile_ssml('<speak xmlns:x="urn:bad"><x:thing>No.</x:thing></speak>', "ssml")

    def test_unsafe_xml_and_resource_limits_are_rejected(self) -> None:
        with self.assertRaisesRegex(SSMLValidationError, "DTD"):
            compile_ssml('<!DOCTYPE speak [<!ENTITY x "hello">]><speak>&x;</speak>', "ssml")
        with self.assertRaisesRegex(SSMLValidationError, "Each <break>"):
            compile_ssml(f'<speak><break time="{MAX_BREAK_MS + 1}ms"/></speak>', "ssml")
        content = "Hello."
        for _ in range(MAX_SSML_NESTING + 1):
            content = f'<prosody rate="100%">{content}</prosody>'
        with self.assertRaisesRegex(SSMLValidationError, "nesting"):
            compile_ssml(f"<speak>{content}</speak>", "ssml")

    def test_capabilities_identify_ssml_h_without_claiming_ipa(self) -> None:
        capabilities = ssml_capabilities()
        self.assertEqual(capabilities["ssml_h"]["namespace"], SSML_H_NAMESPACE)
        self.assertEqual(capabilities["ssml_h"]["voice_scopes"], ["request", "profile"])
        self.assertEqual(
            capabilities["ssml_h"]["default_voice_sample"],
            {
                "language": DEFAULT_DYNAMIC_VOICE_SAMPLE_LANGUAGE,
                "text": DEFAULT_DYNAMIC_VOICE_SAMPLE_TEXT,
                "used_when": "h:sample is omitted",
            },
        )
        self.assertEqual(capabilities["ssml"]["phoneme_alphabets"], ["x-arpabet (English)"])
        self.assertFalse(capabilities["ssml_h"]["description_supported"])


class SSMLExecutionTests(unittest.TestCase):
    def make_session(self, document: str, directory: Path, commit_log: list) -> SSMLExecutionSession:
        plan = compile_ssml(document, "ssml")

        def generate(unit, binding, speed, pitch, tempo, volume, seed):
            del unit, binding, speed, pitch, tempo, volume, seed
            return 1000, np.concatenate((np.zeros(80, dtype=np.int16), np.full(200, 1000, dtype=np.int16), np.zeros(80, dtype=np.int16)))

        return SSMLExecutionSession(
            plan=plan,
            default_binding=SSMLVoiceBinding(),
            request_seed=42,
            request_speed=1.0,
            request_pitch_semitones=0.0,
            request_tempo=1.0,
            request_volume=1.0,
            normalize=False,
            pad_duration=0.0,
            fade_duration=0.0,
            staging_parent=directory,
            resolve_voice=lambda name: SSMLVoiceBinding(name=name),
            resolve_language=resolve_language,
            prepare_voice=lambda definition, text, language, seed, staging: SSMLVoiceBinding(name=definition.name),
            generate_speech=generate,
            commit_profiles=lambda prepared, staging: commit_log.append((prepared, staging)) or {},
        )

    def test_implicit_handoff_is_used_only_without_explicit_break(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            implicit = self.make_session(
                '<speak><voice name="one">One.</voice><voice name="two">Two.</voice></speak>',
                Path(directory),
                [],
            )
            explicit = self.make_session(
                '<speak><voice name="one">One.</voice><break time="0ms"/><voice name="two">Two.</voice></speak>',
                Path(directory),
                [],
            )
            implicit.prepare()
            explicit.prepare()
            _, implicit_audio = implicit.render_array()
            _, explicit_audio = explicit.render_array()
            implicit.close()
            explicit.close()

        self.assertEqual(len(implicit_audio) - len(explicit_audio), IMPLICIT_HANDOFF_MS)

    def test_profile_commit_is_explicit_and_staging_is_cleaned(self) -> None:
        commit_log: list = []
        with tempfile.TemporaryDirectory() as directory:
            session = self.make_session("<speak>Hello.</speak>", Path(directory), commit_log)
            staging = session.staging_dir
            session.prepare()
            session.render_array()
            self.assertEqual(commit_log, [])
            session.commit_profiles()
            self.assertEqual(len(commit_log), 1)
            session.close()
            self.assertFalse(staging.exists())

    def test_suspiciously_short_speech_unit_retries_with_deterministic_seed(self) -> None:
        plan = compile_ssml("<speak>Everything is prepared.</speak>", "ssml")
        seeds: list[int] = []

        def generate(unit, binding, speed, pitch, tempo, volume, seed):
            del unit, binding, speed, pitch, tempo, volume
            seeds.append(seed)
            samples = 100 if len(seeds) == 1 else 1500
            return 1000, np.full(samples, 1000, dtype=np.int16)

        with tempfile.TemporaryDirectory() as directory:
            session = SSMLExecutionSession(
                plan=plan,
                default_binding=SSMLVoiceBinding(),
                request_seed=42,
                request_speed=1.0,
                request_pitch_semitones=0.0,
                request_tempo=1.0,
                request_volume=1.0,
                normalize=False,
                pad_duration=0.0,
                fade_duration=0.0,
                staging_parent=Path(directory),
                resolve_voice=lambda name: SSMLVoiceBinding(name=name),
                resolve_language=resolve_language,
                prepare_voice=lambda *args: SSMLVoiceBinding(),
                generate_speech=generate,
                commit_profiles=lambda items, staging: {},
            )
            session.prepare()
            _sample_rate, waveform = session.render_array()
            session.close()

        self.assertEqual(seeds, [42, 41])
        self.assertEqual(waveform.size, 1500)

    def test_dynamic_voice_turns_reuse_the_voice_definition_seed(self) -> None:
        document = f"""<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis"
          xmlns:h="{SSML_H_NAMESPACE}" xml:lang="en-US">
          <metadata><h:extensions version="1.0">
            <h:voice-definition name="Isabel" age="child" seed="1476293754"/>
            <h:voice-definition name="Mother" gender="female" seed="998282591"/>
          </h:extensions></metadata>
          <voice name="Mother">First turn.</voice>
          <break time="100ms"/>
          <voice name="Isabel">Reply.</voice>
          <break time="100ms"/>
          <voice name="Mother">Final turn.</voice>
        </speak>"""
        plan = compile_ssml(document, "ssml-h", resolve_language=resolve_language)
        generated: list[tuple[str | None, int]] = []

        def generate(unit, binding, speed, pitch, tempo, volume, seed):
            del unit, speed, pitch, tempo, volume
            generated.append((binding.name, seed))
            return 1000, np.full(1500, 1000, dtype=np.int16)

        with tempfile.TemporaryDirectory() as directory:
            session = SSMLExecutionSession(
                plan=plan,
                default_binding=SSMLVoiceBinding(),
                request_seed=42,
                request_speed=1.0,
                request_pitch_semitones=0.0,
                request_tempo=1.0,
                request_volume=1.0,
                normalize=False,
                pad_duration=0.0,
                fade_duration=0.0,
                staging_parent=Path(directory),
                resolve_voice=lambda name: SSMLVoiceBinding(name=name),
                resolve_language=resolve_language,
                prepare_voice=lambda definition, text, language, seed, staging: SSMLVoiceBinding(
                    name=definition.name,
                    generation_seed=seed,
                ),
                generate_speech=generate,
                commit_profiles=lambda items, staging: {},
            )
            session.prepare()
            session.render_array()
            session.close()

        self.assertEqual(
            generated,
            [
                ("Mother", 998282591),
                ("Isabel", 1476293754),
                ("Mother", 998282591),
            ],
        )

    def test_omitted_voice_sample_uses_fixed_internal_reference(self) -> None:
        document = f"""<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis"
          xmlns:h="{SSML_H_NAMESPACE}" xml:lang="en-US">
          <metadata><h:extensions version="1.0">
            <h:voice-definition name="Elisabeth" gender="female"/>
          </h:extensions></metadata>
          <voice name="Elisabeth">Yes. <prosody rate="slow">Everything is prepared.</prosody></voice>
        </speak>"""
        plan = compile_ssml(document, "ssml-h", resolve_language=resolve_language)
        prepared: list[tuple[str, str | None]] = []

        with tempfile.TemporaryDirectory() as directory:
            session = SSMLExecutionSession(
                plan=plan,
                default_binding=SSMLVoiceBinding(),
                request_seed=42,
                request_speed=1.0,
                request_pitch_semitones=0.0,
                request_tempo=1.0,
                request_volume=1.0,
                normalize=False,
                pad_duration=0.0,
                fade_duration=0.0,
                staging_parent=Path(directory),
                resolve_voice=lambda name: SSMLVoiceBinding(name=name),
                resolve_language=resolve_language,
                prepare_voice=lambda definition, text, language, seed, staging: (
                    prepared.append((text, language)) or SSMLVoiceBinding(name=definition.name)
                ),
                generate_speech=lambda *args: (1000, np.full(100, 1000, dtype=np.int16)),
                commit_profiles=lambda items, staging: {},
            )
            session.prepare()
            session.close()

        self.assertEqual(prepared, [(DEFAULT_DYNAMIC_VOICE_SAMPLE_TEXT, "en")])


if __name__ == "__main__":
    unittest.main()
