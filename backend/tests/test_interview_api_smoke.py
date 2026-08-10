"""Smoke test: the spoken interview endpoints, end to end.

Runs a whole exam over HTTP the way the app will: start a session, answer every
question, then score. Uses the mock AI provider, so this proves the exam
sequence and the persistence, not the quality of any band.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_interview_api.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)
from tests._plans import grant_plan  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

PASSWORD = "StrongPass123"

ANSWERS = [
    "My name is Sara Ahmed.",
    "I live in Lahore, in the north of the city.",
    "I am studying software engineering at university.",
    "I usually play cricket with my friends at the weekend.",
    "I have two brothers and one sister.",
    "I prefer the winter because the weather is much cooler.",
    "I listen to music while I am travelling to university.",
    "I would like to visit Japan one day.",
    "I read books mostly in the evening before I sleep.",
]

LONG_TURN = (
    "I would like to talk about my physics teacher, Mrs Karim, who taught me "
    "when I was about sixteen. What made her different was that she never "
    "started with the equation. She would ask a question first and let us argue "
    "about it before she told us anything, which was frustrating at the time "
    "but meant we actually thought about the problem. Because of her I chose "
    "science for my degree, which I had not planned before."
)


def _auth(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/v1/auth/register",
        json={"fullName": "Interview Learner", "email": email, "password": PASSWORD},
    )
    token = client.post(
        "/v1/auth/login", json={"email": email, "password": PASSWORD}
    ).json()["tokens"]["accessToken"]
    h = {"Authorization": f"Bearer {token}"}
    client.post(
        "/v1/onboarding",
        headers=h,
        json={
            "examType": "academic",
            "selfLevel": "intermediate",
            "targetBand": 7.0,
            "examDate": None,
            "dailyMinutes": 30,
            "consentVoice": True,
            "consentAi": True,
        },
    )
    # The spoken interview is a paid feature; a suite that exercises it gives
    # its learner a plan that includes it, as a real candidate would have.
    grant_plan(email)
    return h


def check_audio_endpoints(client: TestClient, h: dict) -> None:
    """The Deepgram/ElevenLabs path, exercised through the mock providers.

    This proves the endpoints, the limits and the error mapping. It cannot
    prove the providers accept our request shape -- that needs one live call
    each, and is deliberately not done here so the suite never spends quota.
    """
    started = client.post("/v1/interview/sessions", headers=h)
    assert started.status_code == 201, started.text
    session_id = started.json()["id"]

    # The examiner's question, spoken. Under the mock this is silent audio, so
    # the assertion is about the contract rather than the sound.
    audio = client.get(f"/v1/interview/sessions/{session_id}/question-audio", headers=h)
    assert audio.status_code == 200, audio.text
    assert audio.headers["content-type"].startswith("audio/")
    assert audio.headers.get("X-TTS-Provider"), "no provider recorded on the audio"

    # A recorded answer advances the exam just as a typed one does.
    before = client.get(f"/v1/interview/sessions/{session_id}", headers=h).json()
    spoken = client.post(
        f"/v1/interview/sessions/{session_id}/answer-audio",
        headers=h,
        files={"audio": ("answer.wav", b"RIFF" + bytes(512), "audio/wav")},
    )
    assert spoken.status_code == 200, spoken.text
    assert spoken.json()["progress"]["answered"] == before["progress"]["answered"] + 1

    # An empty recording is refused before any provider is called.
    empty = client.post(
        f"/v1/interview/sessions/{session_id}/answer-audio",
        headers=h,
        files={"audio": ("answer.wav", b"", "audio/wav")},
    )
    assert empty.status_code in (400, 422), empty.text

    # So is an implausibly large one: an unbounded upload is both a
    # transcription bill and a denial-of-service.
    huge = client.post(
        f"/v1/interview/sessions/{session_id}/answer-audio",
        headers=h,
        files={"audio": ("answer.wav", bytes(11 * 1024 * 1024), "audio/wav")},
    )
    assert huge.status_code in (400, 413, 422), huge.status_code

    # Audio endpoints obey the same ownership rule as the rest of the session.
    other = _auth(client, "interview-audio-other@example.com")
    assert (
        client.get(
            f"/v1/interview/sessions/{session_id}/question-audio", headers=other
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/v1/interview/sessions/{session_id}/answer-audio",
            headers=other,
            files={"audio": ("a.wav", b"RIFF123", "audio/wav")},
        ).status_code
        == 404
    )


def check_recording_alignment(client: TestClient, h: dict) -> None:
    """Recordings line up with the turns they belong to.

    A transcript is a lossy record: "I think, um, maybe" and a confident
    sentence read identically once hesitation has been flattened into text --
    and hesitation is a scored criterion. A learner arguing with their Fluency
    band needs to hear themselves, against the right line.
    """
    started = client.post("/v1/interview/sessions", headers=h)
    session_id = started.json()["id"]

    for text in ("My name is Sara.", "I live in Lahore."):
        client.post(
            f"/v1/interview/sessions/{session_id}/answer",
            headers=h,
            json={"text": text, "source": "typed"},
        )

    r = client.get(f"/v1/interview/sessions/{session_id}/transcript", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()

    # Only the candidate's answers. The examiner's questions are not the
    # learner's words and must not appear in something labelled their
    # transcript.
    texts = [line["text"] for line in body["lines"]]
    assert "My name is Sara." in texts and "I live in Lahore." in texts
    assert "Where do you live?" not in texts

    for line in body["lines"]:
        assert line["phase"]
        # Null is a normal state: recordings are opt-in, so a client must
        # render the transcript without a link rather than treat it as broken.
        assert "audioUrl" in line

    # Ownership follows the session.
    other = _auth(client, "transcript-other@example.com")
    assert (
        client.get(
            f"/v1/interview/sessions/{session_id}/transcript", headers=other
        ).status_code
        == 404
    )


def run() -> None:
    with TestClient(app) as client:
        h = _auth(client, "interview@example.com")

        started = client.post("/v1/interview/sessions", headers=h)
        assert started.status_code == 201, started.text
        s = started.json()
        session_id = s["id"]

        assert s["phase"] == "greeting"
        assert s["action"]["kind"] == "ask"
        assert s["action"]["text"], "the examiner opened with nothing"
        assert s["isComplete"] is False
        assert s["progress"]["answered"] == 0

        # Re-reading must not advance the exam: a client that dropped mid
        # question has to recover it, not skip it.
        again = client.get(f"/v1/interview/sessions/{session_id}", headers=h)
        assert again.status_code == 200
        assert again.json()["action"] == s["action"]
        assert again.json()["progress"]["answered"] == 0

        # Walk the whole exam. Phases are asserted as they arrive rather than
        # assumed, so a reordering shows up here.
        seen: list[str] = []
        answer_index = 0
        current = s
        guard = 0

        while not current["isComplete"]:
            guard += 1
            assert guard < 60, "the exam is not terminating"
            phase = current["phase"]
            seen.append(phase)

            if phase == "part2_cue":
                assert current["action"]["kind"] == "say"
                assert current["action"]["bullets"], "cue card had no bullets"
                text = ""
            elif phase == "part2_prep":
                assert current["action"]["kind"] == "prepare"
                # One minute exactly. This is the rule most often got wrong.
                assert current["action"]["durationSeconds"] == 60
                text = ""
            elif phase == "part2_speaking":
                assert current["action"]["kind"] == "long_turn"
                assert current["action"]["durationSeconds"] == 120
                text = LONG_TURN
            elif phase == "scoring":
                break
            else:
                text = ANSWERS[answer_index % len(ANSWERS)]
                answer_index += 1

            r = client.post(
                f"/v1/interview/sessions/{session_id}/answer",
                headers=h,
                json={"text": text, "source": "android-device"},
            )
            assert r.status_code == 200, (phase, r.text)
            current = r.json()

        assert "greeting" in seen
        assert seen.count("part1") >= 4, seen
        assert "part2_cue" in seen and "part2_prep" in seen
        assert "part2_speaking" in seen and "part2_followup" in seen
        assert seen.count("part3") >= 3, seen

        # An unknown transcript source is refused rather than stored: the whole
        # point of the field is that it can be trusted afterwards.
        bad = client.post(
            f"/v1/interview/sessions/{session_id}/answer",
            headers=h,
            json={"text": "x", "source": "made-up"},
        )
        assert bad.status_code in (400, 422), bad.text

        scored = client.post(f"/v1/interview/sessions/{session_id}/score", headers=h)
        assert scored.status_code == 200, scored.text
        result = scored.json()
        assert result["attemptId"]
        assert result["overallBand"] is not None
        assert result["criteria"], result

        # Scoring twice must not create a second attempt from one exam.
        twice = client.post(f"/v1/interview/sessions/{session_id}/score", headers=h)
        # 422 is this API's validation status; the point is that it refuses.
        assert twice.status_code in (400, 409, 422), twice.text
        assert "already been scored" in twice.text

        # The scored attempt is a real speaking attempt and shows up in history.
        history = client.get("/v1/speaking/history", headers=h)
        assert history.status_code == 200
        assert result["attemptId"] in history.text

        # Another learner cannot read this session, and cannot learn it exists.
        other = _auth(client, "interview-other@example.com")
        assert (
            client.get(f"/v1/interview/sessions/{session_id}", headers=other).status_code
            == 404
        )
        assert (
            client.post(
                f"/v1/interview/sessions/{session_id}/answer",
                headers=other,
                json={"text": "let me in"},
            ).status_code
            == 404
        )

        # Preparation can be skipped, but only during preparation.
        fresh = client.post("/v1/interview/sessions", headers=h).json()
        fresh_id = fresh["id"]
        assert (
            client.post(
                f"/v1/interview/sessions/{fresh_id}/skip-prep", headers=h
            ).status_code
            in (400, 422)
        ), "preparation was skippable during the greeting"

        current = fresh
        guard = 0
        while current["phase"] != "part2_prep":
            guard += 1
            assert guard < 40
            current = client.post(
                f"/v1/interview/sessions/{fresh_id}/answer",
                headers=h,
                json={"text": "ok"},
            ).json()

        skipped = client.post(
            f"/v1/interview/sessions/{fresh_id}/skip-prep", headers=h
        )
        assert skipped.status_code == 200, skipped.text
        assert skipped.json()["phase"] == "part2_speaking"

        # An unfinished exam cannot be scored.
        early = client.post(f"/v1/interview/sessions/{fresh_id}/score", headers=h)
        assert early.status_code in (400, 422), early.text

        check_audio_endpoints(client, h)
        check_recording_alignment(client, h)

    print("INTERVIEW API SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
