export type InfoCard = {
  title: string;
  lines: string[];
};

export const hero = {
  title: "MemoryFeed Docs",
  description:
    "MemoryFeed is a local-first social memory system that helps you capture, index, and retrieve everything you read across social platforms. This documentation site is standalone by design so you can publish it independently with Vercel in minutes.",
  badges: ["Vite + React + TS", "Vercel Ready", "Mobile Friendly"],
};

export const introParagraphs = [
  "MemoryFeed is built for people who consume a lot of content and often remember the idea but forget the source. Instead of relying on bookmarks or browser history, MemoryFeed continuously captures meaningful reading moments from social feeds, then makes them searchable with natural language.",
  "The core principle is local-first memory: all data is stored and processed on your machine. There is no cloud dependency in the default flow, and no API key is required to start. This makes it suitable for private research, personal knowledge tracking, and sensitive browsing workflows.",
  "The platform combines four layers: extension capture, backend normalization, semantic indexing, and a searchable operator UI. Together they provide a practical loop where content is captured passively but retrieved actively with high recall.",
];

export const introCards: InfoCard[] = [
  {
    title: "Capture Layer",
    lines: [
      "Browser extension detects dwell time and sends structured content events to the local backend.",
    ],
  },
  {
    title: "Index Layer",
    lines: [
      "Text and image context are embedded for multilingual retrieval, including Vietnamese and English queries.",
    ],
  },
  {
    title: "Search Layer",
    lines: ["Hybrid keyword + semantic ranking helps recover posts even when exact words are forgotten."],
  },
];

export const quickstartCards: InfoCard[] = [
  { title: "Local Dev", lines: ["npm install", "npm run dev"] },
  { title: "Production Build", lines: ["npm run build", "dist/"] },
  { title: "Preview Build", lines: ["npm run preview", "http://localhost:4173"] },
];

export const demoIntro =
  "Use this script when recording a product demo or onboarding new contributors. It shows the full value loop from passive capture to successful retrieval.";

export const demoSteps = [
  "Start backend and extension, then open a social feed tab.",
  "Pause on 3-5 posts for at least 3 seconds each to trigger capture events.",
  "Include mixed content types: text-only post, meme image, and one long-form article link.",
  "Open MemoryFeed search and run a fuzzy query to simulate imperfect memory.",
  "Verify that top results include source URL, platform context, and enough text snippet to confirm relevance.",
  "Show one additional query in Vietnamese to demonstrate multilingual retrieval quality.",
];

export const demoOutcome =
  "Expected outcome: users understand that MemoryFeed is not just storage. It is a retrieval engine for previously seen information that would otherwise be lost in feed noise.";

export const deploySteps = [
  "npm install",
  "npm run build",
  "In Vercel set Root Directory = ./",
  "Build Command = npm run build",
  "Output Directory = dist",
  "Install Command = npm install",
];

export const reliabilityPoints = [
  "No monorepo root assumptions.",
  "Contains vercel.json at repo root.",
  "Uses resilient Vite build command for Linux CI.",
];
