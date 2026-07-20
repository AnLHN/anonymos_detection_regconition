'use client';

import { FormEvent, useMemo, useState } from 'react';
import { updateRule } from '@/lib/api';
import type { Rule } from '@/lib/types';
import { translateZone, alertLevelText } from '@/lib/alertText';

const WARNING_LEVELS = ['low', 'medium', 'high', 'critical'] as const;
const OUTSIDE_HOURS_RULE = 'unknown_outside_working_hours';
const RESTRICTED_RULE = 'unknown_entered_restricted_area';
const GATE_RULE = 'unknown_loitering_at_gate';
const STABLE_UNKNOWN_RULE = 'stable_unknown_face';
const UNVERIFIED_RESTRICTED_RULE = 'unverified_in_restricted_area';

export default function RulesPanel({
  token,
  rules,
  onRefresh,
  canUpdate = false,
}: {
  token: string;
  rules: Rule[];
  onRefresh: () => Promise<void>;
  canUpdate?: boolean;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const operationRule = useMemo(() => findRule(rules, OUTSIDE_HOURS_RULE), [rules]);
  const restrictedRule = useMemo(() => findRule(rules, RESTRICTED_RULE), [rules]);
  const gateRule = useMemo(() => findRule(rules, GATE_RULE), [rules]);
  const stableUnknownRule = useMemo(() => findRule(rules, STABLE_UNKNOWN_RULE), [rules]);
  const unverifiedRestrictedRule = useMemo(() => findRule(rules, UNVERIFIED_RESTRICTED_RULE), [rules]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!operationRule) {
      setError('Không tìm thấy rule vận hành ngoài giờ.');
      return;
    }
    setSaving(true);
    setError('');
    setMessage('');
    const formData = new FormData(event.currentTarget);
    try {
      const restrictedZones = splitList(String(formData.get('restricted_zones') || ''));
      const gateZones = splitList(String(formData.get('gate_zones') || ''));

      await Promise.all([
        updateRule(token, operationRule.rule_code, {
          is_enabled: formData.get('operation_is_enabled') === 'on',
          warning_level: String(formData.get('operation_warning_level') || operationRule.warning_level).trim(),
          config: {
            ...(operationRule.config || {}),
            start: String(formData.get('operation_start') || operationRule.config?.start || '08:00').trim(),
            end: String(formData.get('operation_end') || operationRule.config?.end || '17:30').trim(),
            cooldown_seconds: Number(formData.get('operation_cooldown_seconds') || operationRule.config?.cooldown_seconds || 300),
          },
        }),
        ...(restrictedRule ? [
          updateRule(token, restrictedRule.rule_code, {
            is_enabled: formData.get('restricted_is_enabled') === 'on',
            warning_level: String(formData.get('restricted_warning_level') || restrictedRule.warning_level).trim(),
            config: {
              ...(restrictedRule.config || {}),
              restricted_zones: restrictedZones,
              cooldown_seconds: Number(formData.get('restricted_cooldown_seconds') || restrictedRule.config?.cooldown_seconds || 300),
            },
          }),
        ] : []),
        ...(gateRule ? [
          updateRule(token, gateRule.rule_code, {
            is_enabled: formData.get('gate_is_enabled') === 'on',
            warning_level: String(formData.get('gate_warning_level') || gateRule.warning_level).trim(),
            config: {
              ...(gateRule.config || {}),
              gate_zones: gateZones,
              frames: Number(formData.get('gate_frames') || gateRule.config?.frames || 12),
              cooldown_seconds: Number(formData.get('gate_cooldown_seconds') || gateRule.config?.cooldown_seconds || 300),
            },
          }),
        ] : []),
        ...(stableUnknownRule ? [
          updateRule(token, stableUnknownRule.rule_code, {
            is_enabled: formData.get('stable_is_enabled') === 'on',
            warning_level: String(formData.get('stable_warning_level') || stableUnknownRule.warning_level).trim(),
            config: {
              ...(stableUnknownRule.config || {}),
              stable_seconds: Number(formData.get('stable_seconds') || stableUnknownRule.config?.stable_seconds || 1.5),
              cooldown_seconds: Number(formData.get('stable_cooldown_seconds') || stableUnknownRule.config?.cooldown_seconds || 300),
            },
          }),
        ] : []),
        ...(unverifiedRestrictedRule ? [
          updateRule(token, unverifiedRestrictedRule.rule_code, {
            is_enabled: formData.get('restricted_is_enabled') === 'on',
            warning_level: String(formData.get('restricted_warning_level') || unverifiedRestrictedRule.warning_level).trim(),
            config: {
              ...(unverifiedRestrictedRule.config || {}),
              restricted_zones: restrictedZones,
              cooldown_seconds: Number(formData.get('restricted_cooldown_seconds') || unverifiedRestrictedRule.config?.cooldown_seconds || 300),
            },
          }),
        ] : []),
      ]);
      setMessage('Đã cập nhật thiết lập vận hành.');
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không lưu được thiết lập vận hành');
    } finally {
      setSaving(false);
    }
  }

  if (!operationRule) {
    return (
      <article className="card rules-card">
        <div className="section-heading compact-heading rules-page-heading">
          <div>
            <h2>Thiết lập vận hành</h2>
            <p>Chưa có rule ngoài giờ để chỉnh sửa.</p>
          </div>
        </div>
        <div className="detail-empty">Hệ thống chưa nạp được rule <strong>{OUTSIDE_HOURS_RULE}</strong> từ backend.</div>
      </article>
    );
  }

  const start = String(operationRule.config?.start || '08:00');
  const end = String(operationRule.config?.end || '17:30');
  const cooldown = Number(operationRule.config?.cooldown_seconds || 300);
  const restrictedZones = getStringList(restrictedRule?.config?.restricted_zones, ['restricted_area', 'server_room', 'warehouse']);
  const gateZones = getStringList(gateRule?.config?.gate_zones, ['gate']);
  const stableSeconds = Number(stableUnknownRule?.config?.stable_seconds || 1.5);
  const stableCooldown = Number(stableUnknownRule?.config?.cooldown_seconds || 300);
  const gateFrames = Number(gateRule?.config?.frames || 12);
  const gateCooldown = Number(gateRule?.config?.cooldown_seconds || 300);
  const restrictedCooldown = Number(restrictedRule?.config?.cooldown_seconds || 300);
  const unverifiedCooldown = Number(unverifiedRestrictedRule?.config?.cooldown_seconds || 300);

  return (
    <article className="card rules-card operation-settings-card">
      <div className="operation-summary-grid">
        <article className="operation-summary-card">
          <span>Khung giờ vận hành</span>
          <strong>{start} - {end}</strong>
        </article>
        <article className="operation-summary-card">
          <span>Người lạ mặc định</span>
          <strong>{stableUnknownRule?.is_enabled ? `Báo sau ${stableSeconds}s` : 'Đang tắt'}</strong>
        </article>
        <article className="operation-summary-card">
          <span>Vùng cảnh báo hạn chế</span>
          <strong>{restrictedZones.map(translateZone).filter(Boolean).join(', ') || 'Chưa cấu hình'}</strong>
        </article>
        <article className="operation-summary-card">
          <span>Khu vực cổng (Gate zone)</span>
          <strong>{gateZones.map(translateZone).filter(Boolean).join(', ') || 'Chưa cấu hình'}</strong>
        </article>
      </div>

      <form className="compact-form operation-settings-form" onSubmit={handleSubmit}>
        <div className="operation-layout-grid">
          {/* Card 1: Quy tắc phát hiện người lạ (Đưa lên đầu) */}
          <section className="operation-config-card">
            <div className="operation-card-header">
              <strong>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                Quy tắc phát hiện người lạ
              </strong>
            </div>
            <div className="operation-settings-grid">
              <label>
                Xác nhận người lạ sau (giây)
                <input name="stable_seconds" type="number" min={0.5} step={0.5} defaultValue={stableSeconds} />
                <small>Thời gian theo dõi trước khi báo. Đặt 0.5s - 1.0s để báo ngay lập tức.</small>
              </label>
              <label>
                Thời gian chờ người lạ (giây)
                <input name="stable_cooldown_seconds" type="number" min={0} step={30} defaultValue={stableCooldown} />
              </label>
              <label>
                Mức độ mặc định người lạ
                <select name="stable_warning_level" defaultValue={stableUnknownRule?.warning_level || 'low'}>
                  {WARNING_LEVELS.map((level) => <option key={level} value={level}>{alertLevelText(level)}</option>)}
                </select>
              </label>
            </div>
            <div className="operation-toggles-row">
              {stableUnknownRule ? (
                <label className="custom-switch">
                  <input name="stable_is_enabled" type="checkbox" defaultChecked={stableUnknownRule.is_enabled} />
                  <span className="switch-slider" />
                  <span>Bật rule người lạ mặc định</span>
                </label>
              ) : null}
            </div>
          </section>

          {/* Card 2: Khung giờ hoạt động ngoài giờ */}
          <section className="operation-config-card">
            <div className="operation-card-header">
              <strong>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                Khung giờ ngoài giờ
              </strong>
              <label className="custom-switch">
                <input name="operation_is_enabled" type="checkbox" defaultChecked={operationRule.is_enabled} />
                <span className="switch-slider" />
                <span>Bật rule</span>
              </label>
            </div>
            <div className="operation-settings-grid">
              <label>
                Bắt đầu giờ làm việc
                <input name="operation_start" type="time" defaultValue={start} required />
                <small>Trước mốc này, hệ thống coi là ngoài giờ.</small>
              </label>
              <label>
                Kết thúc giờ làm việc
                <input name="operation_end" type="time" defaultValue={end} required />
                <small>Sau mốc này, người lạ ngoài giờ sẽ bị cảnh báo.</small>
              </label>
              <label>
                Mức độ cảnh báo ngoài giờ
                <select name="operation_warning_level" defaultValue={operationRule.warning_level}>
                  {WARNING_LEVELS.map((level) => <option key={level} value={level}>{alertLevelText(level)}</option>)}
                </select>
              </label>
              <label>
                Thời gian chờ ngoài giờ (giây)
                <input name="operation_cooldown_seconds" type="number" min={0} step={30} defaultValue={cooldown} />
              </label>
            </div>
          </section>

          {/* Card 3: Vùng cảnh báo và khu vực cổng (Chuyển xuống dưới và rộng ra) */}
          <section className="operation-config-card operation-config-card-wide">
            <div className="operation-card-header">
              <strong>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a10 10 0 0 1 10 10c0 5.523-4.477 10-10 10S2 17.523 2 12A10 10 0 0 1 12 2z"/><path d="M12 8v8"/><path d="M8 12h8"/></svg>
                Vùng cảnh báo & Khu vực cổng
              </strong>
            </div>
            <div className="operation-settings-grid">
              <label>
                Danh sách vùng cảnh báo
                <input name="restricted_zones" defaultValue={restrictedZones.join(', ')} placeholder="restricted_area, server_room" />
                <small>Khớp với các vùng (zone/ROI) được vẽ trên camera.</small>
              </label>
              <label>
                Khu vực cổng (Gate zones)
                <input name="gate_zones" defaultValue={gateZones.join(', ')} placeholder="gate, lobby_gate" />
                <small>Dùng cho rule đứng lâu tại khu vực cổng.</small>
              </label>
              <label>
                Mức độ cảnh báo vùng
                <select name="restricted_warning_level" defaultValue={restrictedRule?.warning_level || 'critical'}>
                  {WARNING_LEVELS.map((level) => <option key={level} value={level}>{alertLevelText(level)}</option>)}
                </select>
              </label>
              <label>
                Thời gian chờ vùng (giây)
                <input name="restricted_cooldown_seconds" type="number" min={0} step={30} defaultValue={restrictedCooldown} />
              </label>
              <label>
                Số khung hình đứng lâu tại cổng
                <input name="gate_frames" type="number" min={1} step={1} defaultValue={gateFrames} />
              </label>
              <label>
                Mức độ cảnh báo cổng
                <select name="gate_warning_level" defaultValue={gateRule?.warning_level || 'medium'}>
                  {WARNING_LEVELS.map((level) => <option key={level} value={level}>{alertLevelText(level)}</option>)}
                </select>
              </label>
              <label>
                Thời gian chờ cổng (giây)
                <input name="gate_cooldown_seconds" type="number" min={0} step={30} defaultValue={gateCooldown} />
              </label>
            </div>
            <div className="operation-toggles-row">
              {restrictedRule ? (
                <label className="custom-switch">
                  <input name="restricted_is_enabled" type="checkbox" defaultChecked={restrictedRule.is_enabled} />
                  <span className="switch-slider" />
                  <span>Bật vùng cảnh báo hạn chế</span>
                </label>
              ) : null}
              {gateRule ? (
                <label className="custom-switch">
                  <input name="gate_is_enabled" type="checkbox" defaultChecked={gateRule.is_enabled} />
                  <span className="switch-slider" />
                  <span>Bật rule đứng lâu tại cổng</span>
                </label>
              ) : null}
            </div>
          </section>
        </div>

        <div className="operation-settings-actions">
          <div className="rule-actions">
            <button type="submit" disabled={saving || !canUpdate}>{saving ? 'Đang lưu...' : 'Lưu thiết lập'}</button>
          </div>
        </div>

        {error ? <span className="error" style={{ display: 'block', marginTop: '12px' }}>{error}</span> : null}
        {message ? <span className="success" style={{ display: 'block', marginTop: '12px' }}>{message}</span> : null}
      </form>
    </article>
  );

}

function findRule(rules: Rule[], ruleCode: string) {
  return rules.find((rule) => rule.rule_code === ruleCode) || null;
}

function getStringList(value: unknown, fallback: string[]) {
  if (!Array.isArray(value)) {
    return fallback;
  }
  return value.map((item) => String(item)).filter(Boolean);
}

function splitList(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean);
}
