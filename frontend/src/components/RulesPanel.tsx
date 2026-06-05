'use client';

import { FormEvent, MouseEvent, useEffect, useMemo, useState } from 'react';
import { createRule, updateRule } from '@/lib/api';
import { ruleDescription, ruleLevelText, ruleTitle } from '@/lib/ruleText';
import type { Rule } from '@/lib/types';

const WARNING_LEVELS = ['low', 'medium', 'high', 'critical'];

type RuleModalMode = 'create' | 'edit' | null;
type RuleField =
  | { name: string; label: string; helper: string; type: 'number'; min?: number; step?: number; defaultValue: number }
  | { name: string; label: string; helper: string; type: 'time'; defaultValue: string }
  | { name: string; label: string; helper: string; type: 'list'; defaultValue: string[] };

const RULE_FIELDS: Record<string, RuleField[]> = {
  stable_unknown_face: [
    {
      name: 'stable_frames',
      label: 'Số frame xác nhận người lạ',
      helper: 'Tăng số này nếu camera hay báo nhầm khi người đi ngang quá nhanh.',
      type: 'number',
      min: 1,
      step: 1,
      defaultValue: 12,
    },
    {
      name: 'cooldown_seconds',
      label: 'Thời gian chờ giữa hai cảnh báo',
      helper: 'Trong khoảng này, cùng một loại cảnh báo sẽ không bắn liên tục.',
      type: 'number',
      min: 0,
      step: 30,
      defaultValue: 300,
    },
  ],
  unknown_outside_working_hours: [
    {
      name: 'start',
      label: 'Giờ bắt đầu làm việc',
      helper: 'Sau mốc này hệ thống xem là trong giờ vận hành.',
      type: 'time',
      defaultValue: '08:00',
    },
    {
      name: 'end',
      label: 'Giờ kết thúc làm việc',
      helper: 'Sau mốc này người lạ sẽ được xem là ngoài giờ làm việc.',
      type: 'time',
      defaultValue: '17:30',
    },
    {
      name: 'cooldown_seconds',
      label: 'Thời gian chờ giữa hai cảnh báo',
      helper: 'Giúp tránh spam cảnh báo khi cùng một người xuất hiện lâu.',
      type: 'number',
      min: 0,
      step: 30,
      defaultValue: 300,
    },
  ],
  unknown_loitering_at_gate: [
    {
      name: 'frames',
      label: 'Số frame đứng lâu tại cổng',
      helper: 'Người lạ phải xuất hiện đủ số frame này tại cổng mới tạo cảnh báo.',
      type: 'number',
      min: 1,
      step: 1,
      defaultValue: 12,
    },
    {
      name: 'gate_zones',
      label: 'Khu vực cổng',
      helper: 'Nhập từng khu vực, phân cách bằng dấu phẩy. Ví dụ: gate, lobby_gate.',
      type: 'list',
      defaultValue: ['gate'],
    },
    {
      name: 'cooldown_seconds',
      label: 'Thời gian chờ giữa hai cảnh báo',
      helper: 'Giúp tránh tạo nhiều cảnh báo khi người lạ vẫn đứng cùng một chỗ.',
      type: 'number',
      min: 0,
      step: 30,
      defaultValue: 300,
    },
  ],
  unknown_entered_restricted_area: [
    {
      name: 'restricted_zones',
      label: 'Khu vực hạn chế',
      helper: 'Nhập các vùng cần bảo vệ, phân cách bằng dấu phẩy. Ví dụ: server_room, warehouse.',
      type: 'list',
      defaultValue: ['restricted_area', 'server_room', 'warehouse'],
    },
    {
      name: 'cooldown_seconds',
      label: 'Thời gian chờ giữa hai cảnh báo',
      helper: 'Giúp tránh spam khi cùng một người lạ còn trong vùng hạn chế.',
      type: 'number',
      min: 0,
      step: 30,
      defaultValue: 300,
    },
  ],
  unverified_in_restricted_area: [
    {
      name: 'restricted_zones',
      label: 'Khu vực hạn chế',
      helper: 'Áp dụng cho người hệ thống chưa xác minh được danh tính.',
      type: 'list',
      defaultValue: ['restricted_area', 'server_room', 'warehouse'],
    },
    {
      name: 'cooldown_seconds',
      label: 'Thời gian chờ giữa hai cảnh báo',
      helper: 'Giúp tránh spam khi camera chưa xác minh được một người trong nhiều frame.',
      type: 'number',
      min: 0,
      step: 30,
      defaultValue: 300,
    },
  ],
};

export default function RulesPanel({
  token,
  rules,
  onRefresh,
  canCreate = false,
  canUpdate = false,
}: {
  token: string;
  rules: Rule[];
  onRefresh: () => Promise<void>;
  canCreate?: boolean;
  canUpdate?: boolean;
}) {
  const [selected, setSelected] = useState<Rule | null>(null);
  const [modalMode, setModalMode] = useState<RuleModalMode>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const modalRule = modalMode === 'edit' ? selected : null;
  const selectedFields = useMemo(() => (modalRule ? RULE_FIELDS[modalRule.rule_code] || [] : []), [modalRule]);

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') closeModal();
    }

    if (modalMode) {
      document.body.classList.add('modal-open');
      window.addEventListener('keydown', closeOnEscape);
    }

    return () => {
      document.body.classList.remove('modal-open');
      window.removeEventListener('keydown', closeOnEscape);
    };
  }, [modalMode]);

  function openCreateModal() {
    setSelected(null);
    setModalMode('create');
    setError('');
    setMessage('');
  }

  function openEditModal(rule: Rule) {
    setSelected(rule);
    setModalMode('edit');
    setError('');
    setMessage('');
  }

  function closeModal() {
    if (saving) return;
    setModalMode(null);
    setSelected(null);
    setError('');
  }

  function closeFromBackdrop(event: MouseEvent<HTMLDivElement>) {
    if (event.target === event.currentTarget) closeModal();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!modalRule) return;
    setError('');
    setMessage('');
    setSaving(true);
    const formData = new FormData(event.currentTarget);
    try {
      await updateRule(token, modalRule.rule_code, {
        is_enabled: formData.get('is_enabled') === 'on',
        warning_level: String(formData.get('warning_level') || '').trim(),
        config: buildRuleConfig(modalRule.rule_code, formData, modalRule.config),
      });
      setModalMode(null);
      setSelected(null);
      setMessage('Đã lưu rule.');
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không lưu được rule');
    } finally {
      setSaving(false);
    }
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setMessage('');
    setSaving(true);
    const formData = new FormData(event.currentTarget);
    try {
      await createRule(token, {
        rule_code: String(formData.get('rule_code') || '').trim(),
        name: String(formData.get('name') || '').trim(),
        is_enabled: formData.get('is_enabled') === 'on',
        warning_level: String(formData.get('warning_level') || '').trim(),
        config: {},
      });
      setMessage('Đã thêm rule mới.');
      setModalMode(null);
      event.currentTarget.reset();
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thêm được rule');
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="card rules-card">
      <div className="section-heading compact-heading rules-page-heading">
        <div>
          <h2>Quy tắc cảnh báo</h2>
          <p>Chỉnh các ngưỡng vận hành bằng form trực quan, không cần thao tác JSON.</p>
        </div>
        {canCreate ? <button type="button" className="rule-add-button" onClick={openCreateModal}>
          Thêm rule
        </button> : null}
      </div>

      {error && !modalMode ? <span className="error">{error}</span> : null}
      {message ? <span className="success">{message}</span> : null}

      <div className="list rule-list">
        {rules.map((rule) => (
          <button className="item item-button rule-item rule-list-item" type="button" key={rule.rule_code} onClick={() => canUpdate && openEditModal(rule)} disabled={!canUpdate}>
            <strong>
              <span>{ruleTitle(rule)}</span>
              <span className="badge">{rule.is_enabled ? 'Đang bật' : 'Đang tắt'}</span>
              <span className={`badge level-${rule.warning_level}`}>{ruleLevelText(rule.warning_level)}</span>
            </strong>
            <span>{ruleDescription(rule)}</span>
          </button>
        ))}
      </div>

      {modalMode ? (
        <div className="rule-modal-backdrop" role="presentation" onMouseDown={closeFromBackdrop}>
          <section className="rule-modal" role="dialog" aria-modal="true" aria-labelledby="rule-modal-title">
            <div className="modal-header">
              <div>
                <span className="modal-kicker">{modalMode === 'edit' ? 'Chỉnh sửa rule' : 'Thêm rule mới'}</span>
                <h2 id="rule-modal-title">{modalMode === 'edit' && modalRule ? ruleTitle(modalRule) : 'Thêm rule'}</h2>
                {modalMode === 'edit' && modalRule ? <p>{ruleDescription(modalRule)}</p> : <p>Chỉ thêm rule khi rule engine đã có logic xử lý mã rule này.</p>}
              </div>
              <button type="button" className="modal-close" aria-label="Đóng cấu hình rule" onClick={closeModal} disabled={saving}>×</button>
            </div>

            {modalMode === 'create' ? (
              <form className="compact-form rule-editor rule-modal-form" onSubmit={handleCreate}>
                <div className="rule-form-grid">
                  <label>
                    Mã rule
                    <input name="rule_code" placeholder="custom_unknown_gate" required />
                  </label>
                  <label>
                    Tên rule
                    <input name="name" placeholder="Người lạ tại cổng phụ" required />
                  </label>
                  <label>
                    Mức độ cảnh báo
                    <select name="warning_level" defaultValue="medium">
                      {WARNING_LEVELS.map((level) => <option key={level} value={level}>{ruleLevelText(level)}</option>)}
                    </select>
                  </label>
                  <label className="inline-check rule-toggle"><input name="is_enabled" type="checkbox" defaultChecked /> Bật cảnh báo này</label>
                </div>
                <div className="rule-actions">
                  <button type="submit" disabled={saving}>{saving ? 'Đang thêm...' : 'Thêm rule'}</button>
                  <button type="button" className="secondary" onClick={closeModal} disabled={saving}>Hủy</button>
                </div>
                {error ? <span className="error">{error}</span> : null}
              </form>
            ) : modalRule ? (
              <form className="compact-form rule-editor rule-modal-form" onSubmit={handleSubmit} key={modalRule.rule_code}>
                <div className="rule-editor-strip">
                  <div className="rule-toggle-field">
                    <span>Trạng thái cảnh báo</span>
                    <label className="inline-check rule-toggle"><input name="is_enabled" type="checkbox" defaultChecked={modalRule.is_enabled} /> Bật cảnh báo này</label>
                  </div>
                  <label className="rule-level-field">
                    Mức độ cảnh báo
                    <select name="warning_level" defaultValue={modalRule.warning_level}>
                      {WARNING_LEVELS.map((level) => <option key={level} value={level}>{ruleLevelText(level)}</option>)}
                    </select>
                  </label>
                </div>

                {selectedFields.length ? (
                  <div className="rule-visual-config">
                    {selectedFields.map((field) => <RuleConfigField key={field.name} field={field} config={modalRule.config || {}} />)}
                  </div>
                ) : (
                  <div className="detail-empty">Rule tùy chỉnh này chưa có form cấu hình riêng. Có thể bật/tắt và đổi mức cảnh báo, config hiện tại sẽ được giữ nguyên.</div>
                )}

                <div className="rule-actions">
                  <button type="submit" disabled={saving}>{saving ? 'Đang lưu...' : 'Lưu rule'}</button>
                  <button type="button" className="secondary" onClick={closeModal} disabled={saving}>Hủy</button>
                </div>
                {error ? <span className="error">{error}</span> : null}
              </form>
            ) : null}
          </section>
        </div>
      ) : null}
    </article>
  );
}

function RuleConfigField({ field, config }: { field: RuleField; config: Record<string, unknown> }) {
  const value = config[field.name];
  const defaultValue = field.type === 'list'
    ? listToText(Array.isArray(value) ? value : field.defaultValue)
    : value ?? field.defaultValue;

  return (
    <label className="rule-config-field">
      <span>{field.label}</span>
      {field.type === 'list' ? (
        <input name={`config_${field.name}`} defaultValue={String(defaultValue)} placeholder={field.defaultValue.join(', ')} />
      ) : (
        <input
          name={`config_${field.name}`}
          type={field.type}
          min={field.type === 'number' ? field.min : undefined}
          step={field.type === 'number' ? field.step : undefined}
          defaultValue={String(defaultValue)}
        />
      )}
      <small>{field.helper}</small>
    </label>
  );
}

function buildRuleConfig(ruleCode: string, formData: FormData, fallback: Record<string, unknown>) {
  const fields = RULE_FIELDS[ruleCode] || [];
  if (!fields.length) {
    return fallback || {};
  }

  const config: Record<string, unknown> = {};
  fields.forEach((field) => {
    const raw = String(formData.get(`config_${field.name}`) || '').trim();
    if (field.type === 'number') {
      config[field.name] = Number(raw || field.defaultValue);
      return;
    }
    if (field.type === 'list') {
      config[field.name] = splitList(raw || field.defaultValue.join(','));
      return;
    }
    config[field.name] = raw || field.defaultValue;
  });

  return config;
}

function splitList(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean);
}

function listToText(value: unknown[]) {
  return value.map((item) => String(item)).join(', ');
}
