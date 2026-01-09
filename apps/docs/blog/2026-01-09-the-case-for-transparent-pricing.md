---
slug: the-case-for-transparent-pricing
title: "The Case for Transparent Pricing in AI Generation"
authors: [weirdfingers]
tags: [philosophy, pricing, transparency, user-rights]
---

# The Case for Transparent Pricing in AI Generation

## The subscription credit shell game

Open any AI image generation platform today and you'll find a familiar pattern: subscription tiers with "credits" that translate to generations through formulas that would make a derivatives trader squint.

**$20/month for 500 credits.** Sounds simple enough. But then:

- Standard generation: 1 credit
- HD generation: 2 credits
- Video generation: 15 credits
- Using model X: 1.5x multiplier
- During peak hours: variable pricing may apply

By the time you've decoded the credit matrix, you've already burned through your allocation trying to figure out what anything actually costs.

This isn't accidental. **Opaque pricing benefits the platform, not the user.**

<!-- truncate -->

## Why subscriptions with credits are fundamentally adversarial

The subscription credit model creates a structural misalignment between platform and user incentives:

### 1. You're paying for headroom you'll never use

Subscription tiers are designed around psychology, not usage. The $20 tier gives you enough credits that you *might* run out. The $40 tier gives you enough that you probably won't. You're paying for insurance against a limit that only exists because the platform created it.

The platform profits from the gap between what you pay for and what you use. That's not a service fee—it's a tax on uncertainty.

### 2. Credit values are arbitrary and changeable

When a platform prices generations in "credits" rather than dollars, they've created a layer of abstraction that serves exactly one purpose: the ability to change effective pricing without announcing a price change.

Last month, HD upscaling cost 2 credits. This month, it costs 3. Your subscription price didn't change, but your purchasing power dropped 33%. No announcement, no changelog, no recourse.

This happens constantly. Credit devaluations are the platform equivalent of shrinkflation—the package looks the same, but there's less inside.

### 3. The complexity is the point

Why do platforms need credit multipliers, tier bonuses, rollover limits, and "fast generation" surcharges? Because complexity obscures comparison.

If Platform A charges $0.04 per generation and Platform B charges $0.06, you can compare them. If Platform A gives you 500 credits for $20 with variable generation costs and Platform B gives you 200 "power tokens" for $15 with different consumption rates, comparison becomes homework. Most people give up and pick the one with better marketing.

**Complexity is a moat against informed consumer choice.**

### 4. Your usage data is their pricing data

Subscription platforms track exactly how you use your credits. They know which models you favor, when you generate most, and how close you get to your limits.

This isn't passive analytics—it's active pricing intelligence. If they notice users consistently maxing out on video generation, expect video credit costs to increase. Your behavior informs their rent extraction.

## What transparent pricing actually looks like

Per-transaction pricing—where you pay the actual cost of each generation, clearly stated in real currency—inverts this dynamic.

**You pay for what you use.** Not an abstract bundle designed around average users who don't exist. Not a tier calculated to make you feel like you're getting a deal while guaranteeing platform margin. Just the cost.

**Costs are auditable.** When Platform A charges $0.04 per image and Platform B charges $0.06, you can calculate exactly what your workflow costs on each. You can optimize. You can make informed decisions.

**Changes are visible.** If a model's cost increases from $0.04 to $0.05, that's a 25% increase. It's obvious. There's no credit abstraction to hide behind.

**No use-it-or-lose-it pressure.** You're not racing to extract value from a subscription before it renews. You're not generating images you don't need because you have "credits left over." You generate when you have something to generate.

## The pass-through model: even more transparent

Boards takes this further. Rather than setting our own per-transaction prices, we use a **pass-through model**: you bring your own API keys to providers like Replicate, FAL, and others. You pay them directly at their published rates.

This means:

- **No markup.** We don't sit between you and the provider extracting margin.
- **No metering.** We don't track your usage to optimize our pricing against you.
- **No surprises.** Provider pricing is published and auditable. If FAL charges $0.03 for an image, you pay FAL $0.03.

We've intentionally removed ourselves from the financial transaction. Our incentive is to make the software useful, not to maximize your generation volume.

## "But subscription pricing is more predictable"

This is the standard defense of subscription credits, and it deserves a direct response.

**Predictability is valuable.** Knowing your maximum spend each month is genuinely useful for budgeting.

But predictable *cost* and predictable *pricing* are different things:

- Subscription: predictable monthly cost, unpredictable value received
- Per-transaction: predictable per-unit cost, variable monthly spend

The question is: which unpredictability do you want to manage?

With subscriptions, you're locked into a fixed payment and hoping you get enough value. With per-transaction, you're paying for actual value and managing your budget actively.

**For sophisticated users, active budget management beats hope.**

If you need strict spending limits, set a budget cap with your API provider. Many support this directly. You get the predictability without the credit abstraction or use-it-or-lose-it pressure.

## Control over your content starts with control over your costs

The pricing conversation connects to a broader philosophy: **who is this tool for?**

Platforms with opaque pricing are optimizing for their own sustainability, not your outcomes. The credit system, the tier psychology, the hidden multipliers—these are all mechanisms to ensure you pay more than you would if you understood exactly what you were buying.

Transparent pricing treats you as an adult capable of making informed decisions. It assumes you can handle knowing that a generation costs $0.04 and deciding whether that's worth it to you.

This respect extends to content control. The same platforms that obscure pricing also tend to:

- Store your generations on their infrastructure
- Train on your outputs (or reserve the right to)
- Maintain deletion policies that serve their storage costs, not your preferences
- Limit or prohibit export of your own work

The thread connecting these practices is the same: **the platform's interests override yours, and opacity makes that easier.**

## Building for users who want to know

Boards is built on a different premise: **you should know what you're paying, what you're getting, and what happens to it afterward.**

- **Pricing:** Pass-through to providers. No markup, no metering, no credit abstraction.
- **Storage:** Your filesystem or your cloud bucket. Not ours.
- **Training:** We don't see your generations. We can't train on what we don't have.
- **Export:** Your data is already local. There's nothing to export.

This isn't a feature list. It's a design philosophy that starts with a question: *what would we build if we assumed users were intelligent adults who wanted to understand and control their tools?*

The answer doesn't include credit obfuscation, storage lock-in, or opacity-as-business-model.

## Try the alternative

If you've been burned by credit devaluation, confused by tier comparisons, or frustrated by use-it-or-lose-it pressure, consider what a transparent alternative feels like.

Bring your own API keys. Pay providers directly at published rates. Store your generations on your own infrastructure. Know exactly what everything costs.

That's the case for transparent pricing. Not because subscriptions are evil, but because opacity benefits platforms at users' expense—and you deserve tools that work for you instead.

---

*Boards is an open-source toolkit for AI-generated content. [Get started](https://github.com/weirdfingers/boards) with transparent pricing today.*
