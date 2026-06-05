import type { Alert } from './types';

const WARNING_TEXT: Record<string, string> = {
  stable_unknown_face: 'Người lạ được phát hiện nhiều lần',
  unknown_outside_working_hours: 'Người lạ xuất hiện ngoài giờ làm việc',
  unknown_loitering_at_gate: 'Người lạ đứng lâu tại khu vực cổng',
  unknown_entered_restricted_area: 'Người lạ đi vào khu vực hạn chế',
  unverified_in_restricted_area: 'Người chưa xác minh đi vào khu vực hạn chế',
};

const LEVEL_TEXT: Record<string, string> = {
  low: 'Thấp',
  medium: 'Trung bình',
  high: 'Cao',
  critical: 'Khẩn cấp',
};

const REVIEW_TEXT: Record<string, string> = {
  new: 'Mới',
  reviewing: 'Đang kiểm tra',
  confirmed: 'Đã xác nhận',
  false_positive: 'Báo sai',
  ignored: 'Bỏ qua',
};

export function alertTitle(alert: Alert) {
  return WARNING_TEXT[alert.warning_type] || humanizeCode(alert.warning_type || alert.status || 'Cảnh báo an ninh');
}

export function alertSummary(alert: Alert) {
  const zone = alert.zone && alert.zone !== 'none' ? ` tại ${humanizeCode(alert.zone)}` : '';
  return `${alert.camera_id}${zone} · ${reviewText(alert.review_status)}`;
}

export function alertLevelText(level: string) {
  return LEVEL_TEXT[level] || humanizeCode(level);
}

export function reviewText(status: string) {
  return REVIEW_TEXT[status] || humanizeCode(status);
}

export function alertDetailReason(alert: Alert) {
  return alert.reason || alertTitle(alert);
}

function humanizeCode(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}
