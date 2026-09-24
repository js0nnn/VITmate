import { useState } from "react";
import { MicOff, X } from "lucide-react";
import { readString, STORAGE_KEYS, writeString } from "../services/storage";
import { speechUnsupportedReason, type SpeechUnsupportedReason } from "../services/speechSupport";
import { Modal } from "./Modal";

const BANNER_TEXT: Record<SpeechUnsupportedReason, { title: string; detail: string }> = {
  unsupported: {
    title: "Speech recognition isn't supported in this browser.",
    detail: "You can keep using Type mode. For voice input, open VITmate in Chrome or Edge.",
  },
  "insecure-context": {
    title: "Voice input needs a secure connection.",
    detail: "Browsers only allow the microphone on https:// pages or localhost. Type mode works normally.",
  },
};

/** Dismissible notice, shown only when the browser cannot provide speech recognition. */
export function SpeechSupportBanner() {
  const [reason] = useState(speechUnsupportedReason);
  const [dismissed, setDismissed] = useState(() => readString(STORAGE_KEYS.speechBannerDismissed) === "1");
  const [learnMoreOpen, setLearnMoreOpen] = useState(false);

  if (!reason) return null;

  const dismiss = () => {
    setDismissed(true);
    writeString(STORAGE_KEYS.speechBannerDismissed, "1");
  };

  return (
    <>
      {!dismissed && (
        <div className="support-banner" role="status">
          <MicOff size={18} className="support-banner-icon" aria-hidden="true" />
          <p className="support-banner-text">
            <strong>{BANNER_TEXT[reason].title}</strong> <span>{BANNER_TEXT[reason].detail}</span>
          </p>
          <button className="support-banner-action" onClick={() => setLearnMoreOpen(true)} aria-haspopup="dialog">
            Learn more
          </button>
          <button className="icon-button support-banner-close" onClick={dismiss} aria-label="Dismiss speech support notice">
            <X size={16} />
          </button>
        </div>
      )}
      <SpeechSupportModal open={learnMoreOpen} onClose={() => setLearnMoreOpen(false)} />
    </>
  );
}

const BROWSERS: { name: string; status: "yes" | "partial" | "no"; note: string }[] = [
  { name: "Google Chrome (desktop & Android)", status: "yes", note: "Recommended" },
  { name: "Microsoft Edge", status: "yes", note: "Recommended" },
  { name: "Safari (macOS & iOS)", status: "partial", note: "Available in recent versions; behaviour varies" },
  { name: "Other Chromium browsers (Brave, Opera …)", status: "partial", note: "API may exist but the speech service can be unavailable" },
  { name: "Firefox", status: "no", note: "Not available by default" },
];

const STATUS_LABEL = { yes: "Supported", partial: "Varies", no: "Not supported" } as const;

export function SpeechSupportModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Modal open={open} onClose={onClose} labelledBy="speech-support-title" className="info-modal">
      <h2 id="speech-support-title" className="info-modal-title">
        Why voice input may not work
      </h2>
      <p>
        VITmate uses the speech recognition that is <strong>built into your web browser</strong> (the Web Speech API).
        Your speech is converted to text by the browser, and only the text is sent to VITmate. Nothing needs to be
        installed, but it only works where the browser provides this feature.
      </p>
      <p>
        Support differs between browsers and versions, and some browsers include the feature but rely on an online
        speech service that may be unavailable. VITmate checks for the feature directly rather than guessing from the
        browser's name.
      </p>

      <table className="support-table">
        <caption className="visually-hidden">Typical browser support for speech recognition</caption>
        <thead>
          <tr>
            <th scope="col">Browser</th>
            <th scope="col">Voice input</th>
          </tr>
        </thead>
        <tbody>
          {BROWSERS.map((browser) => (
            <tr key={browser.name}>
              <td>{browser.name}</td>
              <td>
                <span className={`support-pill is-${browser.status}`}>{STATUS_LABEL[browser.status]}</span>
                <span className="support-note">{browser.note}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="info-modal-footnote">
        For the best voice experience use a recent <strong>Google Chrome</strong> or <strong>Microsoft Edge</strong> on
        an https:// (or localhost) page and allow microphone access. Type mode works in every browser.
      </p>
    </Modal>
  );
}
