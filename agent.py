from __future__ import annotations

import asyncio
from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.agents.multimodal import MultimodalAgent
from livekit.plugins import google

from api import AssistantFnc
from prompts import WELCOME_MESSAGE, get_instructions

load_dotenv()


async def entrypoint(ctx: JobContext):
    # 1. Connect to the LiveKit room and subscribe to tracks
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)

    # 2. Wait until the user joins the room session
    participant = await ctx.wait_for_participant()

    # 3. Configure Gemini Realtime Model with fresh datetime instructions
    instructions = get_instructions()
    model = google.beta.realtime.RealtimeModel(
        model="gemini-2.5-flash-native-audio-preview-12-2025",
        instructions=instructions,
        voice="Aoede",
        temperature=0.7,
        modalities=["audio"],
    )

    # 4. Initialize function context and start the MultimodalAgent
    assistant_fnc = AssistantFnc()
    assistant = MultimodalAgent(model=model, fnc_ctx=assistant_fnc)
    assistant.start(ctx.room, participant)

    # 5. Send initial welcome prompt safely via the active model session in Arabic
    if hasattr(model, "sessions") and len(model.sessions) > 0:
        session = model.sessions[0]
        session.conversation.item.create(
            text=f"Say to the user in a natural, warm, polite Arabic receptionist voice: {WELCOME_MESSAGE}"
        )
        session.response.create()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="Receptionist",
        )
    )