import {
  ArrowLeft,
  ArrowUpRight,
  BriefcaseBusiness,
  Cpu,
  Github,
  Linkedin,
  Mail,
  MapPin,
  Network,
  RadioTower,
  Server,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  Wrench
} from "lucide-react";
import { AnimatePresence, motion, useScroll, useTransform } from "framer-motion";
import { useEffect } from "react";
import { Link, Route, Routes, useLocation, useParams } from "react-router-dom";
import { profile, projects, siteTheme, socials, type Project, type SocialLink } from "./data/portfolio";
import { formatDate, projectTone } from "./utils";

const fadeIn = {
  initial: { opacity: 0, y: 18 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-80px" },
  transition: { duration: 0.58, ease: "easeOut" }
} as const;

function App() {
  const location = useLocation();

  useEffect(() => {
    document.documentElement.dataset.theme = siteTheme;
  }, []);

  return (
    <>
      <TechBackdrop />
      <ScrollProgress />
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<HomePage />} />
          <Route path="/projects/:slug" element={<ProjectPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </AnimatePresence>
    </>
  );
}

function TechBackdrop() {
  return (
    <div className="backdrop" aria-hidden="true">
      <div className="grid-plane" />
      <div className="scanline" />
      <div className="pulse-ring ring-one" />
      <div className="pulse-ring ring-two" />
    </div>
  );
}

function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useTransform(scrollYProgress, [0, 1], [0, 1]);
  return <motion.div className="scroll-progress" style={{ scaleX }} />;
}

function HomePage() {
  return (
    <motion.main className="page" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <SiteNav />
      <Hero />
      <About />
      <SkillMarquee />
      <ProjectIndex />
      <Experience />
      <ContactBand />
    </motion.main>
  );
}

function SiteNav() {
  const displayName = profile.name || "Portfolio Dashboard";

  return (
    <header className="site-nav">
      <Link className="brand" to="/" aria-label={`${displayName} home`}>
        <span className="brand-mark">{brandInitials(displayName)}</span>
        <span>{displayName}</span>
      </Link>
      <nav>
        <a href="/#projects">Projects</a>
        <a href="/#about">About</a>
        <a href="/#contact">Contact</a>
      </nav>
    </header>
  );
}

function Hero() {
  return (
    <section className="hero">
      <motion.div
        className="hero-copy"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: "easeOut" }}
      >
        <p className="eyebrow">
          <TerminalSquare size={16} />
          Systems, automation, and developer tooling
        </p>
        <h1>{profile.name}</h1>
        <p className="hero-role">{profile.role}</p>
        <p className="hero-text">{profile.tagline}</p>
        <div className="hero-actions">
          <a className="button primary" href="#projects">
            <Cpu size={18} />
            View Projects
          </a>
          <a className="button ghost" href={`mailto:${profile.email}`}>
            <Mail size={18} />
            Contact
          </a>
        </div>
      </motion.div>

      <motion.div
        className="system-panel"
        initial={{ opacity: 0, x: 32 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, delay: 0.1, ease: "easeOut" }}
      >
        <div className="panel-topline">
          <span>infra.status</span>
          <span className="live-dot">online</span>
        </div>
        <div className="metric-grid">
          <Metric icon={<Server />} label="Virtualization" value="Proxmox" />
          <Metric icon={<Network />} label="Network Edge" value="MikroTik" />
          <Metric icon={<ShieldCheck />} label="Security" value="Suricata" />
          <Metric icon={<Sparkles />} label="AI Stack" value="Ollama" />
        </div>
        <div className="terminal-window">
          <span>&gt; deploying portfolio --host 0.0.0.0</span>
          <span>&gt; routing ready for Cloudflare Zero Trust</span>
          <span>&gt; projects indexed: {projects.length}</span>
        </div>
      </motion.div>
    </section>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="metric">
      <span>{icon}</span>
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  );
}

function brandInitials(value: string) {
  const words = value.split(/\s+/).filter(Boolean);
  return (words[0]?.[0] || "P") + (words[1]?.[0] || "D");
}

function About() {
  return (
    <motion.section className="section about-section" id="about" {...fadeIn}>
      <div className="section-heading">
        <p className="eyebrow">
          <BriefcaseBusiness size={16} />
          About
        </p>
        <h2>Infrastructure-minded developer with operations instincts.</h2>
      </div>
      <div className="about-grid">
        <p>{profile.about}</p>
        <div className="resume-list">
          {profile.resumeHighlights.map((highlight) => (
            <div className="resume-item" key={highlight}>
              <span />
              <p>{highlight}</p>
            </div>
          ))}
        </div>
      </div>
    </motion.section>
  );
}

function SkillMarquee() {
  const doubled = [...profile.skills, ...profile.skills];
  return (
    <section className="skill-strip" aria-label="Skills">
      <motion.div
        className="skill-track"
        animate={{ x: ["0%", "-50%"] }}
        transition={{ duration: 35, repeat: Infinity, ease: "linear" }}
      >
        {doubled.map((skill, index) => (
          <span className="skill-chip" key={`${skill}-${index}`}>
            {skill}
          </span>
        ))}
      </motion.div>
    </section>
  );
}

function ProjectIndex() {
  return (
    <section className="section" id="projects">
      <motion.div className="section-heading wide" {...fadeIn}>
        <p className="eyebrow">
          <Wrench size={16} />
          GitHub projects
        </p>
        <h2>Project pages generated from public repositories with real uploaded work.</h2>
        <p>
          Each card links to a detail page and the source repo. Update summaries, ordering, or links in
          <code> src/data/portfolio.ts</code>.
        </p>
      </motion.div>
      <div className="project-grid">
        {projects.map((project, index) => (
          <ProjectCard project={project} index={index} key={project.slug} />
        ))}
      </div>
    </section>
  );
}

function ProjectCard({ project, index }: { project: Project; index: number }) {
  return (
    <motion.article
      className={`project-card ${project.status === "Needs manual summary" ? "needs-summary" : ""}`}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.5, delay: Math.min(index * 0.04, 0.28), ease: "easeOut" }}
    >
      <div className="project-card-head">
        <span className="language-pill">{project.language}</span>
        <span>{projectTone(project)}</span>
      </div>
      <h3>{project.name}</h3>
      <p>{project.summary}</p>
      <div className="project-meta">
        <span>{formatDate(project.updated)}</span>
        <span>{project.sizeKb.toLocaleString()} KB</span>
      </div>
      <div className="card-actions">
        <Link className="text-link" to={`/projects/${project.slug}`}>
          Case study <ArrowUpRight size={16} />
        </Link>
        <a className="icon-link" href={project.githubUrl} target="_blank" rel="noreferrer" aria-label={`${project.name} GitHub`}>
          <Github size={18} />
        </a>
      </div>
    </motion.article>
  );
}

function Experience() {
  const items =
    profile.resumeHighlights.length > 0
      ? profile.resumeHighlights.map((highlight) => ({ title: highlight, meta: profile.role }))
      : [
          { title: "GitHub repository importer", meta: "README summaries, stack tags, and project routes" },
          { title: "Configurable theme system", meta: "Matrix, cyan, ember, violet, and mono palettes" },
          { title: "Cross-platform installer flow", meta: "Windows EXE and Linux shell launcher support" }
        ];

  return (
    <motion.section className="section experience-section" {...fadeIn}>
      <div className="section-heading">
        <p className="eyebrow">
          <RadioTower size={16} />
          Operating range
        </p>
        <h2>Built around systems that have to keep working.</h2>
      </div>
      <div className="timeline">
        {items.slice(0, 5).map((item) => (
          <TimelineItem title={item.title} meta={item.meta} key={item.title} />
        ))}
      </div>
    </motion.section>
  );
}

function TimelineItem({ title, meta }: { title: string; meta: string }) {
  return (
    <div className="timeline-item">
      <span />
      <div>
        <h3>{title}</h3>
        <p>{meta}</p>
      </div>
    </div>
  );
}

function ContactBand() {
  return (
    <section className="contact-band" id="contact">
      <div>
        <p className="eyebrow">Open channel</p>
        <h2>Let's build the next reliable thing.</h2>
        <p>{profile.availability}</p>
      </div>
      <div className="social-list">
        {socials.map((social) => (
          <SocialAnchor social={social} key={social.label} />
        ))}
      </div>
    </section>
  );
}

function SocialAnchor({ social }: { social: SocialLink }) {
  const Icon = social.kind === "github" ? Github : social.kind === "linkedin" ? Linkedin : social.kind === "email" ? Mail : MapPin;
  return (
    <a href={social.url} target={social.kind === "email" ? undefined : "_blank"} rel="noreferrer" className="social-link">
      <Icon size={18} />
      {social.label}
    </a>
  );
}

function ProjectPage() {
  const { slug } = useParams();
  const project = projects.find((item) => item.slug === slug);

  if (!project) {
    return <NotFound />;
  }

  return (
    <motion.main className="page detail-page" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <SiteNav />
      <section className="project-hero">
        <Link className="back-link" to="/">
          <ArrowLeft size={18} />
          Back to projects
        </Link>
        <div className="project-hero-grid">
          <div>
            <p className="eyebrow">{project.language} / {projectTone(project)}</p>
            <h1>{project.name}</h1>
            <p>{project.summary}</p>
            <div className="hero-actions">
              <a className="button primary" href={project.githubUrl} target="_blank" rel="noreferrer">
                <Github size={18} />
                Open GitHub
              </a>
              {project.homepage ? (
                <a className="button ghost" href={project.homepage} target="_blank" rel="noreferrer">
                  <ArrowUpRight size={18} />
                  Live Link
                </a>
              ) : null}
            </div>
          </div>
          <div className="repo-panel">
            <span className="language-pill">{project.status}</span>
            <dl>
              <div>
                <dt>Last pushed</dt>
                <dd>{formatDate(project.updated)}</dd>
              </div>
              <div>
                <dt>Repo size</dt>
                <dd>{project.sizeKb.toLocaleString()} KB</dd>
              </div>
              <div>
                <dt>Source</dt>
                <dd>{project.isFork ? "Fork / customization" : "Original repo"}</dd>
              </div>
            </dl>
          </div>
        </div>
      </section>

      <section className="detail-grid">
        <motion.article className="detail-block" {...fadeIn}>
          <h2>What it does</h2>
          <p>{project.impact}</p>
        </motion.article>
        <motion.article className="detail-block" {...fadeIn}>
          <h2>Highlights</h2>
          <ul>
            {project.highlights.map((highlight) => (
              <li key={highlight}>{highlight}</li>
            ))}
          </ul>
        </motion.article>
        <motion.article className="detail-block" {...fadeIn}>
          <h2>Stack</h2>
          <div className="tag-cloud">
            {project.stack.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        </motion.article>
        <motion.article className="detail-block" {...fadeIn}>
          <h2>Repo contents</h2>
          <div className="file-list">
            {project.repoContents.map((item) => (
              <code key={item}>{item}</code>
            ))}
          </div>
        </motion.article>
      </section>
      <ContactBand />
    </motion.main>
  );
}

function NotFound() {
  return (
    <main className="page not-found">
      <SiteNav />
      <section>
        <h1>Page not found</h1>
        <p>The route does not exist yet.</p>
        <Link className="button primary" to="/">
          <ArrowLeft size={18} />
          Return home
        </Link>
      </section>
    </main>
  );
}

export default App;
