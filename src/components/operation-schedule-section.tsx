import { CalendarCheckIcon, CaretDownIcon } from "@phosphor-icons/react";
import {
  OPERATION_PHASE,
  OPERATION_SCHEDULE,
} from "@/lib/operation-schedule";

function monthLabel(value: string) {
  return value.replace("-", ".");
}

export function OperationScheduleSection() {
  return (
    <section className="setting-section span-full operation-schedule">
      <div className="setting-heading">
        <CalendarCheckIcon size={22} />
        <div>
          <h2>運用スケジュール</h2>
          <p>
            戦略を再最適化せず、OOS・Universe・Watchlistを定期的に検証するための運用ルール
          </p>
        </div>
      </div>

      <div className="operation-phase">
        <div className="operation-phase-title">
          <span className="section-label">CURRENT PHASE</span>
          <div>
            <span className="operation-phase-badge">
              {OPERATION_PHASE.label}
            </span>
            <strong>{OPERATION_PHASE.summary}</strong>
          </div>
        </div>
        <dl className="operation-phase-meta">
          <div>
            <dt>開始</dt>
            <dd>{monthLabel(OPERATION_PHASE.frozenSince)}</dd>
          </div>
          <div>
            <dt>次回正式レビュー</dt>
            <dd>{OPERATION_PHASE.formalReviewWindow}</dd>
          </div>
          <div>
            <dt>Frozen Strategy</dt>
            <dd>{OPERATION_PHASE.strategyId}</dd>
          </div>
        </dl>
        <p className="operation-phase-note">
          正式レビューまでは、重大な構造問題がない限りTopN・Momentum
          Weight・MA・Surge・Genre上限などの戦略パラメータを再最適化しません。
        </p>
      </div>

      <div className="schedule-list">
        {OPERATION_SCHEDULE.map((item) => (
          <details className="schedule-item" key={item.id}>
            <summary>
              <span className="schedule-cadence">{item.cadence}</span>
              <span className="schedule-summary-copy">
                <strong>{item.title}</strong>
                <span>{item.timing}</span>
                <small>{item.summary}</small>
              </span>
              <span className="schedule-toggle">
                詳細
                <CaretDownIcon aria-hidden="true" />
              </span>
            </summary>
            <div className="schedule-details">
              <div>
                <h3>実施内容</h3>
                <ul>
                  {item.tasks.map((task) => (
                    <li key={task}>{task}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h3>判断ルール</h3>
                <p>{item.decisionRule}</p>
              </div>
            </div>
          </details>
        ))}
      </div>

      <aside className="operation-principles">
        <span className="section-label">運用原則</span>
        <p>
          過去バックテストはsanity checkとして使用し、過去CAGRを最大化する目的でUniverseを変更しません。
        </p>
        <p>
          Frozen Strategyは正式レビューまで原則固定し、Forward / OOSデータを優先して評価します。
        </p>
      </aside>
    </section>
  );
}
