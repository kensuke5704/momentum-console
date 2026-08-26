"use client";

import { XIcon } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import styles from "./ticker-profile.module.css";

type CompanyProfile = {
  symbol: string;
  companyName: string;
  industry: string | null;
  sector: string | null;
  summary: string | null;
  website: string | null;
  updatedAt: string;
};

type CompanyProfileFile = {
  generatedAt?: string;
  profiles?: Record<string, CompanyProfile>;
};

let profileCache: Record<string, CompanyProfile> | null = null;
let profilePromise: Promise<Record<string, CompanyProfile>> | null = null;

async function loadProfiles(): Promise<Record<string, CompanyProfile>> {
  if (profileCache) return profileCache;
  if (!profilePromise) {
    const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
    profilePromise = fetch(`${base}/data/company-profiles.json`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) return {};
        const body = await response.json() as CompanyProfileFile;
        return body.profiles ?? {};
      })
      .catch(() => ({}));
  }
  profileCache = await profilePromise;
  return profileCache;
}

function CompanyDialog({ symbol, profile, loading, onClose }: { symbol: string; profile: CompanyProfile | null; loading: boolean; onClose: () => void }) {
  useEffect(() => {
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", close);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", close);
    };
  }, [onClose]);

  return <div className={styles.backdrop} onMouseDown={onClose}>
    <div className={styles.modal} role="dialog" aria-modal="true" aria-labelledby={`ticker-profile-${symbol}`} onMouseDown={(event) => event.stopPropagation()}>
      <header className={styles.header}>
        <div className={styles.headerText}>
          <span>{symbol}</span>
          <h2 id={`ticker-profile-${symbol}`}>{profile?.companyName ?? (loading ? "会社情報を読込中" : symbol)}</h2>
          {!loading && profile?.sector && <p>{profile.sector}</p>}
        </div>
        <button type="button" className={styles.closeButton} aria-label="閉じる" onClick={onClose}><XIcon size={18} /></button>
      </header>
      {loading ? <div className={styles.loading}>会社情報を読み込んでいます。</div> : profile ? <div className={styles.body}>
        <div className={styles.metaGrid}>
          <div className={styles.metaItem}><span>会社名</span><strong>{profile.companyName}</strong></div>
          <div className={styles.metaItem}><span>業種</span><strong>{profile.industry ?? profile.sector ?? "情報なし"}</strong></div>
        </div>
        <div>
          <span className={styles.summaryLabel}>概要</span>
          <p className={styles.summary}>{profile.summary ?? "会社概要は現在のデータソースから取得できませんでした。"}</p>
        </div>
        {profile.website && <a className={styles.website} href={profile.website} target="_blank" rel="noreferrer">公式サイトを開く</a>}
      </div> : <div className={styles.unavailable}>この銘柄の会社情報はまだ取得できていません。次回のデータ同期後に再度確認してください。</div>}
    </div>
  </div>;
}

const tickerPattern = /^[A-Z][A-Z0-9.-]{0,9}$/;
const targetSelector = ".top2-grid strong, .dynamic-table td strong";

export function TickerProfileEnhancer() {
  const [symbol, setSymbol] = useState<string | null>(null);
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const enhance = () => {
      document.querySelectorAll<HTMLElement>(targetSelector).forEach((element) => {
        const text = element.textContent?.trim() ?? "";
        if (!tickerPattern.test(text)) return;
        element.dataset.tickerProfileTrigger = "true";
        element.setAttribute("role", "button");
        element.setAttribute("tabindex", "0");
        element.setAttribute("aria-label", `${text}の会社情報を表示`);
        element.classList.add(styles.tickerButton);
      });
    };

    const openFromTarget = async (target: EventTarget | null) => {
      const element = target instanceof Element ? target.closest<HTMLElement>("[data-ticker-profile-trigger='true']") : null;
      if (!element) return false;
      const nextSymbol = element.textContent?.trim() ?? "";
      if (!tickerPattern.test(nextSymbol)) return false;
      setSymbol(nextSymbol);
      setProfile(null);
      setLoading(true);
      const profiles = await loadProfiles();
      setProfile(profiles[nextSymbol] ?? null);
      setLoading(false);
      return true;
    };

    const click = (event: MouseEvent) => { void openFromTarget(event.target); };
    const keydown = (event: KeyboardEvent) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      const target = event.target instanceof Element ? event.target.closest<HTMLElement>("[data-ticker-profile-trigger='true']") : null;
      if (!target) return;
      event.preventDefault();
      void openFromTarget(target);
    };

    enhance();
    const observer = new MutationObserver(enhance);
    observer.observe(document.body, { childList: true, subtree: true });
    document.addEventListener("click", click);
    document.addEventListener("keydown", keydown);
    return () => {
      observer.disconnect();
      document.removeEventListener("click", click);
      document.removeEventListener("keydown", keydown);
    };
  }, []);

  return symbol ? <CompanyDialog symbol={symbol} profile={profile} loading={loading} onClose={() => setSymbol(null)} /> : null;
}
