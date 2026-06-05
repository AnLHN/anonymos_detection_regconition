export function formatDateTime(value?: string | null) {
  const date = parseDate(value);
  if (!date) return 'Không rõ thời gian';
  return new Intl.DateTimeFormat('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(date);
}

export function formatRelativeTime(value?: string | null) {
  const date = parseDate(value);
  if (!date) return 'Không rõ thời gian';
  const diffMs = Date.now() - date.getTime();
  const diffMinutes = Math.round(diffMs / 60_000);
  if (diffMinutes < 1) return 'Vừa xong';
  if (diffMinutes < 60) return `${diffMinutes} phút trước`;
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours} giờ trước`;
  if (diffHours < 48) return 'Hôm qua';
  if (diffHours < 24 * 7) return `${Math.round(diffHours / 24)} ngày trước`;
  return formatDateTime(value);
}

function parseDate(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date;
}
