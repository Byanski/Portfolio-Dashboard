export type SocialLink = {
  label: string;
  url: string;
  kind: "github" | "linkedin" | "email" | "location" | "custom";
};

export type Project = {
  name: string;
  slug: string;
  githubUrl: string;
  homepage?: string;
  language: string;
  status: "Documented" | "Needs manual summary";
  isFork: boolean;
  updated: string;
  sizeKb: number;
  summary: string;
  impact: string;
  stack: string[];
  highlights: string[];
  repoContents: string[];
};

export const siteTheme = "matrix";

export const profile = {
  name: "",
  role: "Developer",
  location: "",
  email: "",
  tagline: "I build practical software and reliable systems.",
  about: "Add a short professional introduction here.",
  availability: "Open to interesting technical projects.",
  resumeHighlights: [],
  skills: []
};

export const socials: SocialLink[] = [];

export const projects: Project[] = [];
