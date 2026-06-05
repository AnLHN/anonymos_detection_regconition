import type { Rule } from './types';

const RULE_TEXT: Record<string, { title: string; description: string }> = {
  stable_unknown_face: {
    title: 'Người lạ được phát hiện nhiều lần',
    description: 'Cảnh báo khi cùng một khuôn mặt lạ xuất hiện qua nhiều khung hình để giảm báo nhầm.',
  },
  unknown_outside_working_hours: {
    title: 'Người lạ ngoài giờ làm việc',
    description: 'Cảnh báo khi phát hiện người lạ ngoài khung giờ vận hành đã cấu hình.',
  },
  unknown_loitering_at_gate: {
    title: 'Người lạ đứng lâu tại cổng',
    description: 'Cảnh báo khi người lạ ở khu vực cổng vượt quá ngưỡng theo dõi.',
  },
  unknown_entered_restricted_area: {
    title: 'Người lạ vào khu vực hạn chế',
    description: 'Cảnh báo khi người lạ đi vào vùng cấm hoặc khu vực nhạy cảm.',
  },
  unverified_in_restricted_area: {
    title: 'Người chưa xác minh vào khu vực hạn chế',
    description: 'Cảnh báo khi hệ thống chưa xác minh được danh tính trong vùng nhạy cảm.',
  },
};

const LEVEL_TEXT: Record<string, string> = {
  low: 'Thấp',
  medium: 'Trung bình',
  high: 'Cao',
  critical: 'Khẩn cấp',
};

export function ruleTitle(rule: Rule) {
  return RULE_TEXT[rule.rule_code]?.title || rule.name || humanizeCode(rule.rule_code);
}

export function ruleDescription(rule: Rule) {
  return RULE_TEXT[rule.rule_code]?.description || 'Rule cảnh báo tùy chỉnh trong hệ thống.';
}

export function ruleLevelText(level: string) {
  return LEVEL_TEXT[level] || humanizeCode(level);
}

function humanizeCode(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}
