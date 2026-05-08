"""Ingest behavioral interview frameworks and Amazon LP question banks into vector store."""
import asyncio
from crisiscoach.agents.background.fact_checker import ingest_document

COLLECTION = "interview_db"

# Core behavioral interview frameworks
FRAMEWORK_CHUNKS = [
    "Behavioral interviews test soft skills: communication, ownership, learning ability, and handling pressure. The goal is to show both your strengths AND your humility and growth mindset — not just competence.",
    "STAR format for behavioral answers: Situation (context), Task (what you were responsible for), Action (what YOU specifically did — not 'we'), Result (quantified outcome or learning). Keep answers under 2-3 minutes.",
    "Two qualities to demonstrate in every behavioral answer: (1) you are strong and capable, (2) you are self-aware and always improving. The combination signals mastery of soft skills.",
    "Amazon's 14 Leadership Principles are the best framework to prepare for behavioral interviews. Every behavioral question maps to at least one LP. Prepare 1-2 stories per LP and you'll be ready for any behavioral interview.",
    "For 'weakness' or 'mistake' questions: name a real specific issue, describe the concrete action you took to fix it, and state the habit or system you adopted to prevent recurrence. Never say 'I work too hard.'",
    "For 'disagreement' questions: show you used data or a demo — not emotion — to persuade. Show you respected the chain of command. Ideally show the outcome benefited everyone.",
    "For 'prioritization' questions: use the Eisenhower Matrix — urgent+important: do now; urgent+not important: delegate; important+not urgent: schedule; neither: defer. Shows structured thinking.",
    "For 'why are you looking for a change' questions: anchor on growth and learning, not frustration. Show the new role aligns with your experience (fast ramp) AND offers something your current role doesn't.",
    "For 'another offer' questions: name 4-5 core values you evaluate jobs on (mission, culture, role alignment, growth), affirm the current company meets them, and explain you're not someone who jumps without strong cause.",
    "For 'not on your resume' questions: choose something that paints you positively — volunteering, NGO work, a passion project, or a personal challenge overcome. It reveals character.",
    "For 'career regret' questions: reframe every decision as a learning. Show the experience clarified what you're actually good at and why you made your next career move. No genuine regret, only clarity.",
]

# Amazon Leadership Principles — what each means + the question bank under it
LP_CHUNKS = [
    "Amazon LP: CUSTOMER OBSESSION — Leaders start with the customer and work backwards. Show you proactively sought customer feedback, made tradeoffs in their favor, and fixed failures quickly. Questions: (1) Tell me about a time when you didn't meet customer expectations — what happened and how did you deal with it? (2) How do you prioritize customer needs when dealing with a large number of customers?",

    "Amazon LP: OWNERSHIP — Leaders act on behalf of the entire company, never 'that's not my job.' Show you took something on without being asked and saw it through. Questions: (1) Tell me about a time when you had to work on a task with unclear responsibilities. (2) Tell me about a time when you took on a task that was beyond your job responsibilities.",

    "Amazon LP: INVENT AND SIMPLIFY — Leaders expect and require innovation and always find ways to simplify. Show you reduced complexity or invented a novel solution. Questions: (1) Describe a time when you found a simple solution to a complex problem. (2) Tell me about a time you had to think outside the box to close a sale or sell your product. (3) What is the most innovative project you've worked on?",

    "Amazon LP: ARE RIGHT A LOT — Leaders have strong judgment and good instincts. Show you made a sound decision with limited data, and also show you were wrong and updated your view. Questions: (1) Tell me about a time when you had to work with insufficient information or incomplete data. (2) Tell me about a time when you were wrong.",

    "Amazon LP: LEARN AND BE CURIOUS — Leaders are never done learning and always seek to improve themselves. Show intellectual curiosity across roles and levels. Questions: (1) Tell me about a time you learned something new from your peer or direct report at work. (2) Tell me about a time you took on work outside your comfort area and found it rewarding.",

    "Amazon LP: THINK BIG — Leaders create and communicate a bold direction that inspires results. Show a moment where you saw the bigger opportunity beyond the immediate task. Questions: (1) Tell me about your most significant professional achievement. (2) Tell me about a time when you were working on an initiative and saw an opportunity to do something much bigger than the initial focus.",

    "Amazon LP: BIAS FOR ACTION — Speed matters. Many decisions are reversible and don't need extensive study. Show you acted decisively with calculated risk. Questions: (1) Provide an example of when you took a calculated risk. (2) Describe a situation when you took the initiative to correct a problem or mistake rather than waiting for someone else.",

    "Amazon LP: FRUGALITY — Accomplish more with less. Constraints breed resourcefulness and self-sufficiency. Show you delivered results without extra resources. Questions: (1) Tell me about a time when you had to rely on yourself to complete a project. (2) Tell me about a time when you had to work with limited time or resources.",

    "Amazon LP: EARN TRUST — Leaders listen attentively, speak candidly, and treat others respectfully even in disagreement. Show psychological safety and difficult conversations handled well. Questions: (1) Describe a time when you had to speak up in a difficult or uncomfortable environment. (2) How do you convince someone who is resistant to what you're trying to do?",

    "Amazon LP: DIVE DEEP — Leaders operate at all levels, stay connected to details, and are skeptical when metrics diverge from anecdote. Show you went beyond the surface to find root cause. Questions: (1) Tell me about the most complicated problem you've had to deal with. (2) Tell me about a time you were trying to understand a problem and had to go down several layers to figure it out — who did you talk to and what info proved most valuable?",

    "Amazon LP: HAVE BACKBONE; DISAGREE AND COMMIT — Leaders are obligated to respectfully challenge decisions, even when uncomfortable. Once decided, commit wholly. Show you pushed back with data, not ego. Questions: (1) Describe a time when you disagreed with the approach of a team member — what did you do? (2) If your direct manager was instructing you to do something you disagreed with, how would you handle it?",

    "Amazon LP: DELIVER RESULTS — Leaders focus on key inputs and deliver results with the right quality and in a timely manner despite setbacks. Show grit and follow-through. Questions: (1) Describe the most challenging situation in your life and how you handled it. (2) Tell me about a time when your team gave up on something but you pushed them to deliver results.",

    "Amazon LP: STRIVE TO BE EARTH'S BEST EMPLOYER — Leaders work every day to create a safer, more productive, and more equitable work environment. Show how you empowered or unblocked others. Questions: (1) How have you been successful at empowering either a person or a group to accomplish a task? (2) Tell me about a time when you were able to remove a serious roadblock preventing your team from making progress.",

    "Amazon LP: SUCCESS AND SCALE BRING RESPONSIBILITY — Leaders create more than they consume and always leave things better than they found them. Show systemic improvement, not just task completion. Questions: (1) Give an example of a time when you've left a project in a better position than you found it. (2) What's the largest impact you've had on your environment?",
]

# Common question patterns with answer structure guidance (abstracted, not personal stories)
ANSWER_PATTERN_CHUNKS = [
    "Answering 'biggest professional mistake not on your resume': (1) Name a specific, real mistake — not vague. (2) Identify the root cause clearly. (3) Describe what you changed in your process to prevent recurrence. (4) Show the next outcome was better because of that change. Demonstrates accountability and growth.",

    "Answering 'what would your manager say you need to work on': Pick something real but not disqualifying. Show you've already identified it, are actively working on it, and have a concrete method (tool, habit, feedback loop). This shows self-awareness and initiative — the opposite of a liability.",

    "Answering 'tell me about a disagreement': Structure — (1) you saw a different path than your manager/peer, (2) you built a case or demo instead of just arguing, (3) you got buy-in through evidence, (4) the outcome was better for everyone. Avoid making the other person look bad.",

    "Answering 'too many responsibilities and how did you prioritize': Use the Eisenhower Matrix framework — urgent+important first, delegate urgent+unimportant, schedule important+not urgent, defer the rest. Shows structured thinking and prevents 'I just worked harder' as the only answer.",

    "Answering 'tell me something not on your resume': Use this to show character — volunteer work, NGO involvement, a side project, a personal challenge you overcame, a creative hobby. Pick something that reveals work ethic, empathy, or curiosity. Keep it genuine.",

    "Answering 'do you have another offer / what would you do': Name 4-5 criteria you use to evaluate roles (mission alignment, growth, culture, role fit, comp). Affirm this company meets them. Express that you invest fully where you are and aren't shopping for marginal gains. Do NOT say you'd leave for more money.",

    "Answering 'why are you looking for a change': Three-part answer — (1) current role is plateauing (learning/growth saturated, not a complaint about people), (2) this role aligns with your skills so you can contribute immediately, (3) you're drawn to this company's mission or culture specifically. Avoid badmouthing anyone.",

    "Answering 'what career decision do you regret': Reframe — no decision is a regret, every one is a data point. Share a role or path that taught you what you're actually best at and enjoy most. Show the clarity it gave you led directly to where you are now. Ends positively.",
]


async def ingest_seed_data():
    all_chunks = FRAMEWORK_CHUNKS + LP_CHUNKS + ANSWER_PATTERN_CHUNKS
    return await ingest_document(
        collection_name=COLLECTION,
        source_url="crisiscoach://seed/behavioral",
        chunks=all_chunks,
        metadata={"domain": "interview_prep", "sub_domain": "behavioral"},
    )


if __name__ == "__main__":
    asyncio.run(ingest_seed_data())
