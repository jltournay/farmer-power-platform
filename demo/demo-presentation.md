---
marp: true
theme: default
paginate: true
backgroundColor: #fff
style: |
  section {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  }
  h1 {
    color: #1a5f2a;
  }
  h2 {
    color: #2d7a3e;
  }
  .columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }
  .highlight {
    background-color: #e8f5e9;
    padding: 1rem;
    border-radius: 8px;
  }
  .metric {
    font-size: 2.5rem;
    font-weight: bold;
    color: #1a5f2a;
  }
  .red { color: #d32f2f; }
  .yellow { color: #f9a825; }
  .green { color: #388e3c; }
---

# Farmer Power Platform

## Transforming Kenya's Tea Quality Through AI-Powered Feedback

![bg right:40%](https://images.unsplash.com/photo-1582793988951-9aed5509eb97?w=800)

---

# The Challenge

## 800,000 smallholder farmers produce 60% of Kenya's tea

<div class="columns">
<div>

### Current Reality
- No real-time quality feedback
- Farmers don't know why grades drop
- Factory waste from low-quality leaves
- Extension officers can't prioritize

</div>
<div>

### The Cost
- **26%** of leaves are Secondary grade
- **KES 2.4M/month** wasted per factory
- Farmers lose bonus payments
- Kenya's export brand at risk

</div>
</div>

---

# The Solution

## AI Grading + Actionable Feedback = Quality Improvement

```
    [QC Analyzer]  -->  [AI Grading]  -->  [SMS/Voice]  -->  [Farmer Action]
         |                   |                 |                   |
    Scans leaves      Classifies by      Sends feedback      Improves
    at factory        TBK leaf type      in Swahili          plucking
```

### The Feedback Loop
Every delivery creates a learning opportunity

---

# TBK Grading Model

## Binary Classification: Primary (Best) vs Secondary

| Leaf Type | Grade | What It Means |
|-----------|-------|---------------|
| Bud | Primary | Perfect plucking |
| 1 leaf + bud | Primary | Fine plucking standard |
| 2 leaves + bud | Primary | Standard fine plucking |
| **3+ leaves + bud** | **Secondary** | **Coarse plucking** |
| Coarse leaf | Secondary | Over-mature leaves |
| Hard banji | Secondary | Dormant shoots |

---

# The Dashboard Categories

## Action-Oriented Workflow for Factory Managers

<div class="columns">
<div>

### <span class="red">ACTION NEEDED</span>
Primary % < 70%
*Assign extension officer*

### <span class="yellow">WATCH</span>
Primary % 70-84%
*Monitor, encourage*

### <span class="green">WIN</span>
Primary % ≥ 85%
*Celebrate, maintain*

</div>
<div>

![width:500px](https://via.placeholder.com/500x300/e8f5e9/1a5f2a?text=Dashboard+Preview)

*Joseph sees exactly who needs help today*

</div>
</div>

---

# The SMS Experience

## 160 Characters That Change Behavior

```
Mama Wanjiku, chai yako:
    82% daraja la kwanza!
Tatizo: majani 3+
Kesho: chuma 2 tu + bud
```

### What Makes It Work
- **Name** - Personal, not a number
- **Primary %** - Progress is visible
- **Top Issue** - Explains WHY
- **Action** - What to do tomorrow

---

<!-- _class: lead -->

# Demo Scenario 1

## Mama Wanjiku's 30-Day Transformation

---

# Week 1: The Problem

## Wanjiku's First Delivery

<div class="columns">
<div>

### Grading Result
<span class="metric red">58%</span> Primary

**Category:** ACTION NEEDED

### Top Issues
- 3+ leaves: **28%** (too many!)
- Coarse leaf: 10%
- Hard banji: 4%

</div>
<div>

### System Actions

1. SMS sent immediately
   *"Tatizo: majani 3+. Afisa atakutembelea."*

2. Joseph sees her in ACTION NEEDED

3. Auto-assigned to Extension Officer Mary

</div>
</div>

---

# Week 2: The Intervention

## Extension Officer Mary Visits

<div class="columns">
<div>

### Mary's Visit (Day 5)
- Demonstrated "2 leaves + bud" technique
- Showed coaching card with photos
- Left printed guide in Swahili

</div>
<div>

### Day 8 Result
<span class="metric yellow">72%</span> Primary

**Improvement:** +14%

### Leaf Type Change
- 3+ leaves: 28% &#8594; **18%** (-10%)
- 2+bud: 30% &#8594; **38%** (+8%)

</div>
</div>

---

# Week 4: Success

## Sustained Improvement

<div class="columns">
<div>

### Day 28 Result
<span class="metric green">87%</span> Primary

**Category:** WIN

### Total Transformation
| Metric | Day 1 | Day 28 |
|--------|-------|--------|
| Primary % | 58% | **87%** |
| 3+ leaves | 28% | **8%** |
| 2+bud | 30% | **42%** |

</div>
<div>

### SMS Celebration

```
Mama Wanjiku, chai yako:
    87% daraja la kwanza!
Pongezi sana!
Wewe ni bingwa wa chai!
```

*"You are a tea champion!"*

</div>
</div>

---

# Wanjiku's Journey

## From Struggling to Thriving in 30 Days

```
         87%  ................................
         |                              |
    80%  |                         |
         |                    |
    70%  |               |
         |          |
    60%  |     |
         |  58%
    50%  +----+----+----+----+----+----+
         Day1  5    8   15   22   28
              Mary visits
```

**+29% improvement** through targeted coaching

---

<!-- _class: lead -->

# Demo Scenario 2

## Kericho Factory's Quarterly Transformation

---

# Month 1: Baseline

## Starting Point for Kericho Tea Factory

<div class="columns">
<div>

### Factory Profile
- **Manager:** Joseph Kiprop
- **Farmers:** 1,247 registered
- **Daily Intake:** ~8,000 kg

</div>
<div>

### Initial Distribution
- <span class="red">ACTION NEEDED:</span> 312 (25%)
- <span class="yellow">WATCH:</span> 623 (50%)
- <span class="green">WIN:</span> 312 (25%)

**Factory Average:** 74% Primary

</div>
</div>

### Waste Impact
- Secondary leaves processed separately (lower value)
- Estimated revenue loss: **KES 2.4M/month**

---

# Month 2: Targeted Intervention

## Joseph Uses the Dashboard

<div class="columns">
<div>

### Dashboard Actions
- Identified 312 ACTION NEEDED farmers
- Assigned to 2 Extension Officers
- Prioritized top 50 by volume

### Extension Team
- Visited 50 priority farmers
- Demo at 8 collection points
- Distributed 200 coaching cards

</div>
<div>

### Platform (Automatic)
- 1,247 weekly SMS updates
- 347 farmers called Voice IVR
- Thursday pattern identified

### Month 2 Results
- <span class="red">ACTION:</span> 312 &#8594; **187** (-10%)
- <span class="green">WIN:</span> 312 &#8594; **375** (+5%)

**Factory Average:** 78% Primary (+4%)

</div>
</div>

---

# Month 3: Sustained Improvement

## Quality Culture Established

<div class="columns">
<div>

### Final Distribution
- <span class="red">ACTION:</span> 62 (5%)
- <span class="yellow">WATCH:</span> 498 (40%)
- <span class="green">WIN:</span> 687 (**55%**)

**Factory Average:** 84% Primary

</div>
<div>

### Business Impact
| Metric | Value |
|--------|-------|
| Secondary volume | **-26%** |
| Monthly savings | **KES 1.8M** |
| Farmer bonuses | **+KES 3M/mo** |
| Platform cost | KES 150K/mo |
| **ROI** | **11x** |

</div>
</div>

---

# Factory Transformation

## 90 Days of Progress

| Metric | Month 1 | Month 3 | Change |
|--------|---------|---------|--------|
| Factory Average | 74% | 84% | **+10%** |
| WIN Farmers | 25% | 55% | **+30%** |
| ACTION Farmers | 25% | 5% | **-20%** |
| Waste Savings | - | KES 1.8M/mo | **New** |

### The Virtuous Circle
Better farming &#8594; Better grades &#8594; Higher prices &#8594; Motivated farmers

---

<!-- _class: lead -->

# Demo Scenario 3

## Tea Board of Kenya - National Impact

---

# Year 1: Pilot Phase

## 12 Factories Show the Way

<div class="columns">
<div>

### Pilot Coverage
- Factories: 12 / 68 (18%)
- Farmers: 52,000 / 800,000 (6.5%)
- Regions: Kericho, Nandi, Nyeri

</div>
<div>

### Pilot vs Non-Pilot (Q4)

| Metric | Pilot | Non-Pilot |
|--------|-------|-----------|
| Primary % | 82.4% | 71.8% |
| YoY Change | +8.2% | +1.4% |
| Export-ready | 48% | 22% |

</div>
</div>

### Key Finding
**6x faster improvement** in pilot factories

---

# Year 2: National Rollout

## Projected National Impact

<div class="columns">
<div>

### Rollout Plan
- Q1: 20 factories (Murang'a, Kisii)
- Q2: 18 factories (Bomet, Meru)
- Q3: Remaining 18 factories
- Q4: Full coverage

**Target:** 68 factories, 800,000 farmers

</div>
<div>

### Projected Metrics
| Metric | Current | Year 2 |
|--------|---------|--------|
| National Primary | 72.2% | **82.0%** |
| Export-ready | 22% | **45%** |
| Export revenue | - | **+$7.2M/yr** |
| Farmer bonuses | - | **+KES 2.9B/yr** |

</div>
</div>

---

# The Kenya Premium Story

## From Quality Data to Export Brand

<div class="columns">
<div>

### Current State
- National Primary: 72.2%
- Export-ready (85%+): 22%
- "Kenya Tea" is commodity

</div>
<div>

### Vision (Year 3)
- National Primary: 85%+
- Export-ready: 60%+
- **"Kenya Premium Tea"** certification

</div>
</div>

### Economic Impact
- Additional export revenue: **$7.2M/year**
- Farmer income increase: **+KES 3,600/year per farmer**
- Total farmer payments: **+KES 2.9B/year**

---

# The Platform at a Glance

## How It All Fits Together

```
                    +-------------------+
                    |   Tea Board of    |
                    |      Kenya        |  National trends
                    +-------------------+
                            |
          +-----------------+-----------------+
          |                                   |
+-------------------+               +-------------------+
|  Factory Manager  |               |  Factory Manager  |  Dashboard
|    (Joseph)       |               |    (Other)        |
+-------------------+               +-------------------+
          |                                   |
    +-----+-----+                       +-----+-----+
    |           |                       |           |
+-------+   +-------+               +-------+   +-------+
|Farmer |   |Farmer |               |Farmer |   |Farmer |  SMS/Voice
+-------+   +-------+               +-------+   +-------+
```

---

# Why It Works

## The Science of Behavior Change

<div class="columns">
<div>

### Immediate Feedback
Same-day SMS after every delivery
*"What did I do right/wrong?"*

### Specific Actions
Not "do better" but "pick 2 leaves + bud"
*"What exactly should I change?"*

</div>
<div>

### Visible Progress
Primary % trend shows improvement
*"Am I getting better?"*

### Human Connection
Extension officer visits, Voice IVR
*"Someone cares about my success"*

</div>
</div>

---

# Technology Stack

## Real React + MongoDB Demo

<div class="columns">
<div>

### Frontend
- React + TypeScript
- Production-ready code
- Desktop-first, tablet-friendly

### Backend
- FastAPI
- MongoDB
- Real API contracts

</div>
<div>

### Demo Data Seeder
```bash
python scripts/seed_demo_data.py \
  --factory "Kericho Tea" \
  --farmers 50 \
  --days 30 \
  --scenarios improvement
```

*Not mockups - working software*

</div>
</div>

---

# Named Demo Farmers

## Characters for User Testing

| Name | Journey | Demo Purpose |
|------|---------|--------------|
| Mama Wanjiku Muthoni | 58% &#8594; 87% | Hero transformation |
| Baba James Kiprop | 72% &#8594; 88% | WATCH &#8594; WIN |
| Mama Grace Chepkoech | 45% &#8594; 52% | Difficult case |
| Baba Peter Ochieng | 85% &#8594; 88% | Already good |
| Mama Faith Nyambura | 78% &#8594; 78% | Control group |

---

# Questions to Validate

## What We Need to Learn

<div class="columns">
<div>

### For Joseph (Factory Manager)
- Can you find who needs help?
- How would you assign an extension officer?
- Is the information actionable?

### For Factory Owner
- What's the ROI story?
- Would you pay KES 150K/month?

</div>
<div>

### For Regulator (TBK)
- Which region needs support?
- How does this help export brand?

### For Investor
- How does this help farmers?
- What's the ecosystem play?
- Is this defensible?

</div>
</div>

---

# Next Steps

## From Presentation to Product

<div class="columns">
<div>

### Immediate (This Week)
1. Test scenarios with 3-5 stakeholders
2. Gather feedback on flows
3. Validate assumptions

### Short Term (2 Weeks)
4. Build React prototype
5. Seed demo data
6. User testing with Joseph

</div>
<div>

### Medium Term (1 Month)
7. API integration
8. SMS gateway setup
9. Pilot with 1 factory

### Launch
10. 3-month pilot
11. Measure improvement
12. Scale to 12 factories

</div>
</div>

---

<!-- _class: lead -->

# Thank You

## Questions?

**Farmer Power Platform**
*Transforming Kenya's Tea Quality*

---

# Appendix: SMS Templates

## All Message Variants

| Category | SMS Template |
|----------|--------------|
| **WIN** | "Mama Wanjiku, chai yako: 88% daraja la kwanza! Pongezi! Endelea hivyo!" |
| **WATCH** | "Mama Wanjiku, chai yako: 74% daraja la kwanza. Tatizo: majani 3+. Chuma 2 tu + bud!" |
| **ACTION** | "Mama Wanjiku, chai yako: 58% daraja la kwanza. Tatizo: majani magumu. Afisa atakutembelea." |
| **First** | "Karibu Farmer Power! Mama Wanjiku, chai yako ya kwanza: 85% daraja la kwanza!" |

---

# Appendix: Coaching Cards

## Visual Guides for Each Issue

<div class="columns">
<div>

### 3+ Leaves (59% of issues)
- Pick only 2 leaves + bud
- Harvest every 5-7 days
- Don't rush before market

</div>
<div>

### Coarse Leaf (30% of issues)
- Pick young, soft leaves only
- Avoid old, hard leaves
- Check for yellow color

### Hard Banji (11% of issues)
- Exclude hard shoots
- Prune bushes regularly
- May need fertilizer

</div>
</div>

---

# Appendix: Voice IVR Flow

## For Low-Literacy Farmers

```
1. Dial *384#
2. Select language (Swahili/Kikuyu/Luo)
3. Hear personalized greeting
4. Hear Primary % and trend
5. Hear top issue explained
6. Hear action steps (3 max)
7. Press 1 to replay, 2 for help, 9 to end
```

**Duration:** 2-3 minutes
**Languages:** Swahili, Kikuyu, Luo