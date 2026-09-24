import { Brain, Database, ExternalLink, Mic, Sparkles } from "lucide-react";
import { LogoMark, Wordmark } from "./Logo";
import { Modal } from "./Modal";

export const GITHUB_URL = "https://github.com/js0nnn/VITmate.git";

interface AboutModalProps {
  open: boolean;
  onClose: () => void;
}

/** GitHub "mark" (Primer Octicons, MIT licence); brand icons are not part of lucide. */
function GitHubMark({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden="true" fill="currentColor">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}

export function AboutModal({ open, onClose }: AboutModalProps) {
  return (
    <Modal open={open} onClose={onClose} labelledBy="about-title" className="about-modal">
      <div className="about-hero">
        <LogoMark size={48} />
        <h2 id="about-title" className="about-title">
          <Wordmark />
        </h2>
        <p className="about-tagline">Your VIT Campus Companion</p>
        <p className="about-subtitle">Voice-Enabled Deep Learning Chatbot</p>
      </div>

      <p className="about-description">
        VITmate answers questions about VIT academics, admissions, campus life and careers. You can type or speak.
        A fine-tuned transformer classifies each question's intent, and the answer comes from a knowledge base built from
        official VIT and other authoritative sources.
      </p>

      <ul className="about-features">
        <li><Mic size={16} aria-hidden="true" /> Browser speech recognition</li>
        <li><Brain size={16} aria-hidden="true" /> Transformer intent classifier</li>
        <li><Database size={16} aria-hidden="true" /> Curated VIT knowledge base</li>
      </ul>

      <div className="about-credit">
        <span className="about-credit-label">Developed by</span>
        <strong>B. Jaison Edward</strong>
        <span>Reg. No: 23BAI0094</span>
      </div>

      <a className="about-github" href={GITHUB_URL} target="_blank" rel="noopener noreferrer">
        <GitHubMark />
        <span className="about-github-text">
          <strong>Source code on GitHub</strong>
          <span>github.com/js0nnn/VITmate</span>
        </span>
        <ExternalLink size={15} aria-hidden="true" />
      </a>

      <section className="about-ai" aria-labelledby="about-ai-title">
        <h3 id="about-ai-title">
          <Sparkles size={15} aria-hidden="true" /> AI-Assisted Development
        </h3>
        <p>
          ChatGPT and Claude were used as professional AI-assisted development tools for architecture planning,
          implementation support, debugging, documentation, testing, and technical review. Project direction, design
          decisions and final review were carried out by the developer.
        </p>
      </section>

      <p className="about-disclaimer">
        A student lab project and not an official VIT service. Always confirm important details on{" "}
        <a href="https://vit.ac.in/" target="_blank" rel="noopener noreferrer">vit.ac.in</a>.
      </p>
    </Modal>
  );
}
