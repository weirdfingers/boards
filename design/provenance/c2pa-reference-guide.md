# C2PA Reference Guide for Digital Asset Provenance

> A curated collection of references for implementing content provenance and authenticity in generative AI workflows.

**Document Version:** 1.0  
**Created:** January 2026  
**Purpose:** Research guide for implementing "heritage" (provenance DAG) tracking in the Boards OSS project

---

## Table of Contents

1. [Overview](#overview)
2. [Official C2PA Specifications](#official-c2pa-specifications)
3. [Open Source SDKs & Tools](#open-source-sdks--tools)
4. [IPTC Standards (Complementary)](#iptc-standards-complementary)
5. [Industry Adoption & Case Studies](#industry-adoption--case-studies)
6. [Government & Policy Documents](#government--policy-documents)
7. [Critical Analysis & Security Research](#critical-analysis--security-research)
8. [Background Standards](#background-standards)
9. [Verification Tools](#verification-tools)
10. [Key Concepts Summary](#key-concepts-summary)

---

## Overview

### What is C2PA?

The **Coalition for Content Provenance and Authenticity (C2PA)** is an open technical standard for embedding cryptographically signed provenance metadata into digital media files. It enables tracking of:

- **Origin** - Where/how content was created
- **Modifications** - What edits were made and by what tools
- **Ingredients** - Source assets used to create derived content (the "heritage" concept)
- **AI Disclosure** - Whether generative AI was used and with what parameters

### Why C2PA for Boards?

C2PA natively supports **ingredient assertions** - the ability to embed the full provenance chain (transitive closure of inputs) directly within an asset. When an ingredient contains C2PA manifests, those manifests are inserted into the new asset's manifest store, preserving the complete heritage even after download.

### Key Technical Characteristics

| Feature | Description |
|---------|-------------|
| **Storage** | JUMBF (JPEG Universal Metadata Box Format) embedded in files |
| **Integrity** | Cryptographic signatures with optional trusted timestamps (RFC 3161) |
| **Extensibility** | Custom assertions supported alongside standard ones |
| **Compatibility** | Works with JPEG, PNG, TIFF, WebP, MP4, MOV, PDF, and more |

---

## Official C2PA Specifications

### Core Specifications

| Resource | Description | URL |
|----------|-------------|-----|
| **Technical Specification v2.2** | The authoritative technical standard (current version) | https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html |
| **C2PA Explainer** | Accessible, non-normative overview of concepts | https://spec.c2pa.org/specifications/specifications/2.2/explainer/Explainer.html |
| **Implementation Guidance** | Best practices for implementers | https://spec.c2pa.org/specifications/specifications/2.2/guidance/Guidance.html |
| **Security Considerations** | Threat model and mitigations | https://spec.c2pa.org/specifications/specifications/1.0/security/Security_Considerations.html |

### Supporting Documents

| Resource | Description | URL |
|----------|-------------|-----|
| **Guiding Principles** | Design philosophy and requirements | https://c2pa.org/principles/ |
| **Content Credentials White Paper** | Executive overview (PDF) | https://c2pa.org/wp-content/uploads/sites/33/2025/10/content_credentials_wp_0925.pdf |
| **C2PA Public Draft Security** | Latest security considerations | https://c2pa.org/public-draft/Security_Considerations.html |

### Specification Archive

Previous versions for reference:

- v2.1 (2024-09-20): https://spec.c2pa.org/specifications/specifications/2.1/specs/_attachments/C2PA_Specification.pdf
- v1.3 (2023-03-29): https://spec.c2pa.org/specifications/specifications/1.3/specs/_attachments/C2PA_Specification.pdf
- v1.0 (2021-12-21): https://spec.c2pa.org/specifications/specifications/1.0/specs/_attachments/C2PA_Specification.pdf

---

## Open Source SDKs & Tools

### Primary SDK (Rust)

| Resource | Description | URL |
|----------|-------------|-----|
| **c2pa-rs GitHub** | Core Rust implementation | https://github.com/contentauth/c2pa-rs |
| **c2pa crate (crates.io)** | Rust package | https://crates.io/crates/c2pa |
| **API Documentation** | Rust docs | https://docs.rs/c2pa |
| **Release Notes** | Version history and migration guides | https://github.com/contentauth/c2pa-rs/blob/main/docs/release-notes.md |

### Language Bindings

| Language | Repository | Notes |
|----------|------------|-------|
| **Python** | https://github.com/contentauth/c2pa-python | PyO3 bindings to c2pa-rs |
| **C/C++** | https://github.com/contentauth/c2pa-c | Native C bindings |
| **JavaScript/TypeScript** | https://github.com/contentauth/c2pa-js | WASM-based |
| **Node.js** | https://github.com/contentauth/c2pa-node-v2 | Native Node bindings |
| **iOS** | https://github.com/contentauth/c2pa-ios | Swift bindings |

### Content Authenticity Initiative Resources

| Resource | Description | URL |
|----------|-------------|-----|
| **CAI GitHub Organization** | All official repositories | https://github.com/contentauth |
| **CAI Documentation Site** | Comprehensive guides | https://opensource.contentauthenticity.org/ |
| **Rust SDK Docs** | Getting started with Rust | https://opensource.contentauthenticity.org/docs/rust-sdk/ |
| **Working with Manifests** | Key concepts explained | https://opensource.contentauthenticity.org/docs/manifest/understanding-manifest/ |

### Specialized Libraries

| Resource | Description | URL |
|----------|-------------|-----|
| **Atlas C2PA Library** | ML-specific C2PA extensions (Intel Labs) | https://github.com/IntelLabs/atlas-c2pa-lib |

### General Metadata Tools

| Resource | Description | URL |
|----------|-------------|-----|
| **ExifTool** | Reads C2PA/JUMBF metadata (and much more) | https://exiftool.org/ |

---

## IPTC Standards (Complementary)

IPTC metadata is widely supported and integrates with C2PA. Use IPTC for human-readable descriptive fields alongside C2PA for cryptographic provenance.

### Photo Metadata

| Resource | Description | URL |
|----------|-------------|-----|
| **IPTC Photo Metadata Standard 2025.1** | Current specification | https://www.iptc.org/std/photometadata/specification/IPTC-PhotoMetadata |
| **Photo Metadata User Guide** | Implementation guidance | https://www.iptc.org/std/photometadata/documentation/userguide/ |
| **IPTC Standard Overview** | Version history and downloads | https://www.iptc.org/standards/photo-metadata/iptc-standard/ |

### Video Metadata

| Resource | Description | URL |
|----------|-------------|-----|
| **IPTC Video Metadata Hub** | Video metadata standard | https://iptc.org/standards/video-metadata-hub/ |
| **Video Metadata Hub User Guide** | Implementation guidance | https://www.iptc.org/std/videometadatahub/userguide/ |

### AI-Specific Guidance

| Resource | Description | URL |
|----------|-------------|-----|
| **AI-Generated Image Metadata Guidance** | How to tag synthetic media | https://iptc.org/news/iptc-publishes-metadata-guidance-for-ai-generated-synthetic-media/ |
| **New AI Properties (2025.1)** | AI Prompt, System, Version fields | https://iptc.org/news/iptc-photo-metadata-standard-2025-1-adds-ai-properties/ |
| **Draft AI Properties Discussion** | Public comment on proposed fields | https://iptc.org/news/draft-for-public-comment-new-photo-metadata-fields-for-ai-generated-content/ |

---

## Industry Adoption & Case Studies

### Major Platform Implementations

| Organization | Description | URL |
|--------------|-------------|-----|
| **Google** | C2PA in Google Photos, Pixel cameras | https://blog.google/technology/ai/google-gen-ai-content-transparency-c2pa/ |
| **OpenAI** | C2PA in DALL-E / ChatGPT images | https://help.openai.com/en/articles/8912793-c2pa-in-chatgpt-images |
| **Meta** | IPTC metadata for AI labeling | https://iptc.org/news/meta-announces-support-for-iptc-metadata-in-generative-ai-images/ |
| **Google (IPTC)** | Digital Source Type usage | https://iptc.org/news/google-announces-use-of-iptc-metadata-for-generative-ai-images/ |

### Press Releases & Announcements

| Resource | Description | URL |
|----------|-------------|-----|
| **OpenAI Joins C2PA** | Steering committee announcement | https://spec.c2pa.org/post/openai_pr/ |

### Cultural Heritage & Government

| Resource | Description | URL |
|----------|-------------|-----|
| **Library of Congress C2PA Initiative** | G+LAM community of practice | https://blogs.loc.gov/thesignal/2025/07/c2pa-glam/ |
| **Carter Center Election Observation** | Real-world deployment lessons | https://www.electoralintegrityproject.com/eip-blog/2024/9/20/content-credentialed-media-in-election-observation-missions-first-lessons-learned |

### Industry Analysis

| Resource | Description | URL |
|----------|-------------|-----|
| **C2PA and the AI Supply Chain** | Enterprise perspective | https://aicompetence.org/c2pa-ai-supply-chain-verifying-authenticity/ |
| **AI for Good Summit Coverage** | Industry panel discussion | https://aiforgood.itu.int/transparency-and-trust-in-the-age-of-ai-generated-content/ |

---

## Government & Policy Documents

### U.S. Government

| Resource | Description | URL |
|----------|-------------|-----|
| **NSA/CISA Content Credentials Guide** | Cybersecurity guidance (PDF, Jan 2025) | https://media.defense.gov/2025/Jan/29/2003634788/-1/-1/0/CSI-CONTENT-CREDENTIALS.PDF |
| **NIST AI 100-4** | Synthetic content transparency approaches | https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-4.pdf |
| **C2PA Response to NIST** | Industry feedback (PDF) | https://downloads.regulations.gov/NIST-2024-0001-0030/attachment_1.pdf |

### International

The EU AI Act (Article 50) requires transparency for AI-generated content. C2PA is positioned as a compliance mechanism.

---

## Critical Analysis & Security Research

Understanding limitations is crucial for robust implementation.

### Academic & Independent Analysis

| Resource | Description | URL |
|----------|-------------|-----|
| **World Privacy Forum Analysis** | Comprehensive privacy/trust review | https://worldprivacyforum.org/posts/privacy-identity-and-trust-in-c2pa/ |
| **Hacker Factor: C2PA's Worst Case** | Critical security analysis | https://www.hackerfactor.com/blog/index.php?/archives/1013-C2PAs-Worst-Case-Scenario.html |
| **Hacker Factor Blog (latest)** | Ongoing C2PA critique (Pixel 10 analysis) | https://www.hackerfactor.com/blog/index.php |

### Industry Security Perspectives

| Resource | Description | URL |
|----------|-------------|-----|
| **SC Media: C2PA Analysis** | Balanced security assessment | https://www.scworld.com/perspective/how-c2pa-can-safeguard-the-truth-from-digital-manipulation |
| **Undercode Testing: CR Badge Analysis** | Vulnerability demonstration | https://undercodetesting.com/the-illusion-of-authenticity-how-c2pas-cr-badge-fails-as-a-true-ai-content-guardian/ |

### Key Vulnerabilities to Consider

1. **Metadata Stripping** - C2PA data can be removed entirely (mitigated by soft bindings/watermarks)
2. **Trust Model Limitations** - Signatures prove who signed, not whether content is truthful
3. **Platform Support Gaps** - Many social platforms still strip metadata on upload
4. **Key Compromise** - Signing key security is critical but out-of-spec

---

## Background Standards

### Metadata Formats

| Standard | Description | URL |
|----------|-------------|-----|
| **XMP (Extensible Metadata Platform)** | ISO standard for embedded metadata | https://en.wikipedia.org/wiki/Extensible_Metadata_Platform |
| **Vorbis Comments** | Audio metadata for OGG/FLAC | https://wiki.xiph.org/VorbisComment |
| **ID3 Tags** | Audio metadata for MP3 | https://archive.org/details/id3v2.3.0 |
| **ID3 Wikipedia** | Overview | https://en.wikipedia.org/wiki/ID3 |

### Related Standards Bodies

| Organization | Focus | URL |
|--------------|-------|-----|
| **IPTC** | News/media metadata standards | https://iptc.org/ |
| **CAWG** | Creator assertions working group | Referenced in C2PA specs |
| **EIDR** | Entertainment identifiers | https://eidr.org/ |

---

## Verification Tools

### Official Validators

| Tool | Description | URL |
|------|-------------|-----|
| **Content Credentials Verify** | Adobe's official web validator | https://contentcredentials.org/verify |

### Development Tools

| Tool | Description | URL |
|------|-------------|-----|
| **c2patool** | CLI tool included with c2pa-rs | https://github.com/contentauth/c2pa-rs |
| **ExifTool** | Read C2PA via `-JUMBF:all` | https://exiftool.org/ |
| **IPTC GetPMD** | Read IPTC photo metadata | Referenced at iptc.org |

---

## Key Concepts Summary

### C2PA Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     C2PA Manifest Store                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   Active Manifest                    │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │  Assertions:                                        │    │
│  │    - c2pa.actions (created, edited, etc.)          │    │
│  │    - c2pa.ingredient (references to source assets) │    │
│  │    - stds.iptc (descriptive metadata)              │    │
│  │    - c2pa.hash.data (content binding)              │    │
│  │    - Custom assertions...                          │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │  Claim (references all assertions)                  │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │  Claim Signature (cryptographic seal)               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Ingredient Manifests                    │    │
│  │         (recursively embedded from inputs)           │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Ingredient Tracking (Heritage)

When creating a derived asset from inputs:

1. Each input's C2PA manifest (if present) is copied into the new asset's manifest store
2. An `ingredient` assertion references each input with:
   - Thumbnail (optional)
   - Hash of original asset
   - Relationship type (e.g., `parentOf`, `componentOf`)
   - Reference to the ingredient's manifest within the store
3. The full provenance chain is preserved recursively

### Trust Model

```
                    ┌─────────────────┐
                    │   Trust List    │
                    │  (C2PA managed) │
                    └────────┬────────┘
                             │
                             ▼
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   Signer    │─────▶│ Certificate  │─────▶│  Claim Signature │
│ (Software/  │      │  Authority   │      │   Validation     │
│  Hardware)  │      └──────────────┘      └─────────────────┘
└─────────────┘                                     │
                                                    ▼
                                           ┌─────────────────┐
                                           │ Validation State │
                                           │ - Valid          │
                                           │ - Invalid        │
                                           │ - Trusted        │
                                           └─────────────────┘
```

---

## Next Steps for Boards Implementation

1. **Prototype with c2pa-python** - Quick iteration on manifest structure
2. **Define custom assertions** - For Boards-specific metadata (generation parameters, model versions)
3. **Implement ingredient tracking** - Map your existing DB relationships to C2PA ingredients
4. **Consider signing strategy** - Self-signed for development, CA-issued for production
5. **Plan for soft bindings** - Watermarking as fallback when metadata is stripped
6. **Test with validators** - Ensure interoperability with Content Credentials Verify

---

## Document Information

**Compiled from:** Web research conducted January 2026  
**Sources:** C2PA official documentation, IPTC standards, industry announcements, security research  
**License:** This reference document is provided for research purposes

---

*For questions or updates to this document, refer to the original conversation context.*
