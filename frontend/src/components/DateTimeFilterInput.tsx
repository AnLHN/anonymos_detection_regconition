'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import DatePicker from 'react-datepicker';
import { format } from 'date-fns';
import { vi } from 'date-fns/locale';

export default function DateTimeFilterInput({
  value,
  onChange,
  boundary,
  placeholder = 'dd/mm/yyyy',
}: {
  value?: string;
  onChange: (value: string) => void;
  boundary: 'start' | 'end';
  placeholder?: string;
}) {
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);
  const parsedValue = useMemo(() => filterValueToDate(value), [value]);
  const [draftDate, setDraftDate] = useState<Date | null>(parsedValue);

  useEffect(() => {
    setDraftDate(parsedValue);
  }, [parsedValue]);

  useEffect(() => {
    if (!open) {
      return;
    }

    function handlePointerDown(event: MouseEvent) {
      if (!wrapperRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    }

    document.addEventListener('mousedown', handlePointerDown);
    window.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      window.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  const displayValue = parsedValue ? format(parsedValue, 'dd/MM/yyyy') : placeholder;

  return (
    <div className="filter-datetime-shell" ref={wrapperRef}>
      <button
        type="button"
        className={`filter-datetime-trigger ${parsedValue ? 'has-value' : ''}`}
        onClick={() => {
          setDraftDate((current) => current || new Date());
          setOpen((current) => !current);
        }}
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        <span>{displayValue}</span>
        <span className="filter-datetime-trigger-icon" aria-hidden="true">◷</span>
      </button>

      {open ? (
        <div className="filter-datetime-popover" role="dialog" aria-label="Chọn ngày">
          <div className="filter-datetime-popover-header">
            <strong>Chọn ngày</strong>
            <div className="filter-datetime-quick-actions">
              <button type="button" className="secondary" onClick={() => applyPreset('today', boundary, onChange, setDraftDate)}>Hôm nay</button>
              <button type="button" className="secondary" onClick={() => applyPreset('monthStart', boundary, onChange, setDraftDate)}>Đầu tháng</button>
              <button type="button" className="secondary" onClick={() => applyPreset('monthEnd', boundary, onChange, setDraftDate)}>Cuối tháng</button>
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setDraftDate(null);
                  onChange('');
                  setOpen(false);
                }}
              >
                Xóa
              </button>
            </div>
          </div>

          <DatePicker
            inline
            selected={draftDate || new Date()}
            onChange={(date: Date | null) => updateDatePart(date, boundary, onChange, setDraftDate)}
            locale={vi}
            dateFormat="dd/MM/yyyy"
            showMonthDropdown
            showYearDropdown
            dropdownMode="select"
            todayButton="Hôm nay"
            calendarClassName="filter-datetime-calendar filter-datetime-inline-calendar"
          />

          <div className="filter-datetime-footer">
            <button type="button" className="filter-datetime-confirm" onClick={() => setOpen(false)}>Xong</button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function filterValueToDate(value?: string) {
  if (!value) {
    return null;
  }
  const [datePart, timePart = '00:00'] = value.split('T');
  const [year, month, day] = datePart.split('-').map(Number);
  const [hour, minute] = timePart.split(':').map(Number);
  if (!year || !month || !day) {
    return null;
  }
  return new Date(year, month - 1, day, hour || 0, minute || 0, 0, 0);
}

function dateToFilterValue(date: Date | null) {
  if (!date) {
    return '';
  }
  return format(date, "yyyy-MM-dd'T'HH:mm");
}

function updateDatePart(
  date: Date | null,
  boundary: 'start' | 'end',
  onChange: (value: string) => void,
  setDraftDate: (value: Date | null) => void,
) {
  if (!date) {
    setDraftDate(null);
    onChange('');
    return;
  }
  const next = withBoundaryTime(date, boundary);
  setDraftDate(next);
  onChange(dateToFilterValue(next));
}

function applyPreset(
  preset: 'today' | 'monthStart' | 'monthEnd',
  boundary: 'start' | 'end',
  onChange: (value: string) => void,
  setDraftDate: (value: Date | null) => void,
) {
  const next = new Date();
  if (preset === 'monthStart') {
    next.setDate(1);
  } else if (preset === 'monthEnd') {
    next.setMonth(next.getMonth() + 1, 0);
  }
  const normalized = withBoundaryTime(next, boundary);
  setDraftDate(normalized);
  onChange(dateToFilterValue(normalized));
}

function withBoundaryTime(date: Date, boundary: 'start' | 'end') {
  const next = new Date(date);
  if (boundary === 'start') {
    next.setHours(0, 0, 0, 0);
  } else {
    next.setHours(23, 59, 0, 0);
  }
  return next;
}