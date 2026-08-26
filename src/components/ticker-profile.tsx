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

export function TickerProfile({ symbol }: { symbol: string }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState<CompanyProfile | null>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", close);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", close);
    };
  }, [open]);

  const show = async () => {
    setOpen(true);
    setLoading(true);
    const profiles = await loadProfiles();
    setProfile(profiles[symbol] ?? null);
    setLoading(false);
  };

  return <>
    <button
      type="button"
      className={styles.tickerButton}
      onClick={(event) => { event.stopPropagation(); void show(); }}
      aria-label={`${symbol}の会社情報を表示`}
    >
      {symbol}
    </button>
    {open && <div className={styles.backdrop} onMouseDown={() => setOpen(false)}>
      <div className={styles.modal} role="dialog" aria-modal="true" aria-labelledby={`ticker-profile-${symbol}`} onMouseDown={(event) => event.stopPropagation()}>
        <header className={styles.header}>
          <div className={styles.headerText}>
            <span>{symbol}</span>
            <h2 id={`ticker-profile-${symbol}`}>{profile?.companyName ?? (loading ? "会社情報を読込中" : symbol)}</h2>
            {!loading && profile?.sector && <p>{profile.sector}</p>}
          </div>
          <button type="button" className={styles.closeButton} aria-label="閉じる" onClick={() => setOpen(false)}><XIcon size={18} /></button>
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
    </div>}
  </>;
}
