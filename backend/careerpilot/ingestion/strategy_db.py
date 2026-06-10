"""Ingest job search strategy content into vector store — segmented by experience level."""
import asyncio
from careerpilot.agents.background.fact_checker import ingest_document

COLLECTION = "job_strategy"

# ── Universal fundamentals ────────────────────────────────────────────────────
UNIVERSAL_CHUNKS = [
    "70-80% of jobs are filled through networking, not job boards. Warm outreach outperforms cold applications by 5x. Referrals bypass the ATS entirely and land you directly in front of a hiring manager.",
    "Target 5-10 companies at depth rather than spray-and-pray across 50 job postings. Deep targeting means knowing the company's recent earnings, product launches, and open headcount before you apply.",
    "LinkedIn Easy Apply has the lowest conversion rate of any application method. Direct recruiter or hiring manager outreach converts 3x better. Spend 80% of your effort on outreach, 20% on applications.",
    "When starting a new search, reactivate dormant connections first — people who already know you are fastest to refer. A warm email to a former manager or teammate will outperform 50 cold LinkedIn messages.",
    "The LinkedIn hashtag hack: search '[Role] #hiring' in LinkedIn's search bar → filter 'From my network' + 'Past week'. These are hiring managers who posted they're actively hiring. Apply via the link in the post, then send a personalized connection request immediately after.",
    "Personalized connection request template after applying: 'Hi [Name], I just applied to [Role] at [Company]. It caught my eye because [specific value 1] and [specific value 2] — I'd love to make an immediate impact on [specific team goal]. Looking forward to connecting.' Keep it under 300 characters.",
    "Follow-up template after connecting: 'Thanks for connecting! Who on your hiring team should I be keeping an eye out for?' This moves the conversation forward without being pushy.",
    "One-week no-response follow-up: 'Hi — just following up on my application for [Role]. I'm genuinely excited about [specific thing] and would love to know who on the hiring team I should stay in touch with.' Polite, specific, signals real interest.",
    "Outreach goal: send 5 personalized recruiter or hiring-manager messages per week minimum. Personalized means referencing something specific about their team, product, or a recent company event — not just the role title.",
    "Avoid the 'rejection spiral': rejections are expected. At senior levels, 50-200 applications for one offer is statistically normal. Track your pipeline as a funnel metric — not a personal score.",
]

# ── Entry-level (0–2 years experience) ───────────────────────────────────────
ENTRY_LEVEL_CHUNKS = [
    "Entry-level job search (0-2 years): your biggest asset is speed and volume. Apply to 10-15 roles per week but customize each cover letter or message. Hiring managers can spot a template in 3 seconds.",
    "Entry-level: leverage your university alumni network aggressively. Alumni are 5x more likely to respond to outreach than strangers. Search your school on LinkedIn, filter by company, and reach out with a direct ask: 'Would you be open to a 15-minute call about what it's like to work on your team?'",
    "Entry-level: internship-to-full-time conversion is the highest-yield path. If you have former internship managers, they are your #1 referral source — reach out within the first week of your job search.",
    "Entry-level: early-stage startups (Series A-B) are often more willing to hire less experienced engineers who show strong fundamentals and learning velocity. Apply to 3-4 startups per week alongside larger targets.",
    "Entry-level: GitHub profile and personal projects carry weight equal to internship experience. Make sure each project has a clear README, deployed demo link, and quantified impact (e.g. 'serves 500 active users').",
    "Entry-level: career fairs and company info sessions are high-value because recruiters expect to meet early-career candidates there. Attend at least 2 per month during active search.",
    "Entry-level compensation: don't lowball yourself. Research levels.fyi for the role and company tier. Entry-level SWE at FAANG is $130K-$200K all-in. At mid-tier tech, $90K-$140K. Know your floor before any conversation.",
    "Entry-level: aim to get 1 FAANG or top-25 company application in per week. Even if you don't get the role, the interview practice at that bar raises your performance everywhere else.",
]

# ── Mid-level (3–6 years experience) ─────────────────────────────────────────
MID_LEVEL_CHUNKS = [
    "Mid-level job search (3-6 years): your network is now your strongest asset — use it. Proactively reach out to former colleagues, skip-level managers, and people you've worked cross-functionally with. These are your highest-conversion referral sources.",
    "Mid-level: you should be targeting L4/L5 (Google/Meta scale) or equivalent. Don't let recruiters downlevel you without pushback. Know your target level by studying job descriptions and asking your recruiter explicitly: 'What level is this role targeted at?'",
    "Mid-level: system design rounds are now a primary filter. Prepare 3-4 canonical designs (URL shortener, news feed, ride-sharing dispatch, distributed rate limiter). Practice explaining trade-offs, not just the design itself.",
    "Mid-level: companies want proof of ownership and impact, not just execution. Prepare 2-3 stories where you drove a project from 0 to production — including stakeholder alignment, technical decisions, and business outcome.",
    "Mid-level: target companies going through hyper-growth or a major product pivot. They need experienced engineers who can operate with minimal hand-holding. These companies promote fast and pay competitively.",
    "Mid-level compensation: $180K-$350K all-in at tier-1 tech. $140K-$220K at tier-2. Never accept the first offer — at this level, a 20-30% negotiation improvement is common and expected. Counter every offer.",
    "Mid-level: if you've been at the same company for 3+ years, your market comp is likely 20-40% below what you'd get externally. Use this search as a reset opportunity — external moves average 15-20% compensation jumps.",
    "Mid-level: warm up the recruiting pipeline 2-3 months before you actually want to leave. Take recruiter calls even if you're not sure — it calibrates your market value and builds relationships you'll use later.",
]

# ── Senior (7–12 years experience) ───────────────────────────────────────────
SENIOR_LEVEL_CHUNKS = [
    "Senior job search (7-12 years): networking is virtually the only channel that works at scale. 90% of senior roles are filled before they're publicly posted. If you're only applying to job boards, you're seeing the leftovers.",
    "Senior: your target contacts are engineering directors, VPs of Engineering, and CTOs at growth-stage companies, and senior recruiters at top tech firms. Identify 10 target contacts per week and send a personal, specific note.",
    "Senior: executive search firms (recruiters who specialize in senior placement) are a high-yield channel that entry/mid-level candidates can't access. Reach out to 5-10 technical executive recruiters proactively and send your resume + what you're looking for.",
    "Senior: L6/L7 (Google/Meta) or Staff/Principal conversations require a 'scope narrative' — a concise story of the largest-scope problem you've ever owned, the organizational ambiguity you navigated, and the multi-team alignment you drove. Prepare this before any senior loop.",
    "Senior: don't pursue roles where you'd be the only senior engineer. Look for teams where you'd be one of 2-3 seniors — it signals a culture of peer learning and reduces the risk of becoming a single point of failure with no growth ceiling.",
    "Senior: compensation negotiation at this level involves RSU refreshes, sign-on bonuses, and level negotiations — not just base salary. Know the difference between L5 and L6 comp at your target companies before entering any loop.",
    "Senior: portfolio of technical writing (design docs, RFCs, public blog posts) is a differentiator at this level. A senior candidate with 2-3 published technical articles will have more inbound recruiter outreach than one without.",
    "Senior: the 'peer reference check' is now standard. Contact 4-5 former peers and managers pre-emptively and ask them to be references. Align on which specific projects you want them to highlight.",
]

# ── Staff / Principal (12+ years) ────────────────────────────────────────────
STAFF_LEVEL_CHUNKS = [
    "Staff/Principal job search (12+ years): the market is thin and highly relationship-driven. Posting on a job board is almost never the path. Your next role will come from a former colleague, an advisor relationship, or a board-level introduction.",
    "Staff/Principal: your search should include a VC portfolio scan. Identify 5-10 VCs investing in your domain, find the portfolio companies, and reach out to the founding team directly. Investors often make warm introductions.",
    "Staff/Principal: you are being evaluated on organizational impact, not just technical output. Prepare stories that demonstrate: (1) influencing direction across multiple teams, (2) building engineering culture, (3) making bets that paid off at a company level.",
    "Staff/Principal: consider fractional CTO or technical advisor roles during your search. These generate income, expand your network, and often convert to full-time roles. Platforms like Toptal and expert networks are a starting point.",
    "Staff/Principal: your LinkedIn headline, 'About' section, and top 3 featured posts must signal thought leadership — not just a job history. Post at least once per week during a search. Senior recruiters and founders read your content before reaching out.",
    "Staff/Principal compensation: $400K-$1M+ all-in at top-tier companies. Equity negotiation (cliff timing, acceleration, refreshes) is often more impactful than base. Work with a compensation consultant or lawyer for offers above $500K.",
]

# ── Role-type specific strategies ─────────────────────────────────────────────
ROLE_TYPE_CHUNKS = [
    "Software Engineering job search: system design and coding are the two filters. Balance your prep 60% coding (LeetCode medium/hard) and 40% system design. At senior levels, flip to 30/70. The system design bar rises sharply with seniority.",
    "Product Management job search: PM interviews test product sense, execution, and analytical thinking. Prepare 3 product critique stories, 2 metrics/analytics problems, and 2 cross-functional conflict stories. Know the company's product deeply before the loop.",
    "Data Science / ML job search: companies want proof you've shipped models to production — not just built notebooks. Prepare a case study of a model you trained, deployed, monitored, and iterated. Include business impact, not just model metrics.",
    "ML Engineering job search: the bar is both ML knowledge and systems engineering. Prepare distributed training architecture, model serving systems, and MLOps pipeline design. Know the tradeoffs between latency, throughput, and cost for inference.",
    "Engineering Management job search: prepare stories about growing engineers (not just technical output), handling underperformance, and making organizational decisions. The loop will test your ability to articulate values, not just tactics.",
    "Design / UX job search: your portfolio is the primary filter. Each case study must include: problem framing, user research evidence, iteration history, and measurable outcome. Presentation skill is evaluated as heavily as the work itself.",
]

# ── Career transition strategies ──────────────────────────────────────────────
TRANSITION_CHUNKS = [
    "Career transition (IC to manager): frame every story around the team's output, not your individual contribution. Show you've already been doing manager work informally: mentoring, running meetings, driving alignment. Avoid transitioning cold — internal moves are far easier.",
    "Career transition (manager to IC): be honest about why you're returning. The most credible reason is 'I miss the technical depth and want to stay closer to the code.' Don't frame it as a step down — frame it as a focus choice.",
    "Career transition (industry pivot): target companies with transferable domain overlap. A fintech to healthtech move is easier than fintech to gaming. Identify the 3-5 core skills that transfer and lead with those in every outreach message.",
    "Career transition (startup to BigTech): BigTech loops are process-heavy and bar-raising. Treat it as a 3-month preparation project. The biggest gaps are usually system design depth and behavioral story polish — both are learnable.",
    "Career transition (BigTech to startup): startups want proof you can operate with less structure. Prepare stories where you drove something with no playbook, hit a roadblock with no one to escalate to, and still delivered. Avoid stories where your success depended on a large team.",
    "Career transition (gap explanation): if you're between roles, address it directly and briefly if asked: focus on what you're targeting and why, not on how you left. Pivot immediately to your goal and what makes you a strong fit.",
]

# ── Pipeline management and timing ────────────────────────────────────────────
PIPELINE_CHUNKS = [
    "Job search pipeline rule: always have 3-5 active processes running in parallel. Never go all-in on one company until you have an offer in hand. Parallel pipelines give you negotiating leverage and protect against single-point failures.",
    "Interview timing strategy: try to schedule final rounds at multiple companies within the same 1-2 week window. Simultaneous offers give you real leverage. Stagger your applications 2-3 weeks apart to create this overlap.",
    "Runway-based urgency: if you have less than 8 weeks of runway, shift to high-volume outreach immediately. Target 20 applications per week plus 10 networking messages. Speed beats optimization when cash is running low.",
    "Runway-based patience: if you have 16+ weeks of runway, optimize for fit over speed. Apply to fewer roles with more preparation per application. Bad-fit jobs accepted under financial pressure cost 6-12 months to escape.",
    "ATS optimization: use the exact keywords from the job description in your resume. ATS systems score resumes on keyword density before a human sees them. Run your resume through jobscan.co against each job description before applying.",
    "Recruiter call script: 'Can you tell me the timeline for this role, how many candidates you're currently considering, and what a strong candidate looks like in your view?' These three questions give you information to calibrate your effort and negotiate from.",
]


async def ingest_seed_data():
    all_chunks = (
        UNIVERSAL_CHUNKS
        + ENTRY_LEVEL_CHUNKS
        + MID_LEVEL_CHUNKS
        + SENIOR_LEVEL_CHUNKS
        + STAFF_LEVEL_CHUNKS
        + ROLE_TYPE_CHUNKS
        + TRANSITION_CHUNKS
        + PIPELINE_CHUNKS
    )
    return await ingest_document(
        collection_name=COLLECTION,
        source_url="careerpilot://seed/strategy",
        chunks=all_chunks,
        metadata={"domain": "job_strategy"},
    )


if __name__ == "__main__":
    asyncio.run(ingest_seed_data())
