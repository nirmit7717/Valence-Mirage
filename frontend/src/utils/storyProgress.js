// Story progress for the HUD, from the server's `story_progress`
// ({ chapter, total, act_id, act_title, beat_title, beat_type, final, ... }).

/**
 * @returns {null | { chapter: number, total: number, label: string, act: string, percent: number, final: boolean }}
 *   null when the session has no campaign outline.
 */
export function describeProgress(progress) {
  const total = Number(progress?.total) || 0;
  if (!total) return null;
  const chapter = Math.min(Math.max(Number(progress.chapter) || 1, 1), total);
  const actTitle = (progress.act_title || '').trim();
  const act = progress.act_id ? `Act ${progress.act_id}${actTitle ? ` · ${actTitle}` : ''}` : actTitle;
  return {
    chapter,
    total,
    label: `Chapter ${chapter} of ${total}`,
    act,
    // Share of chapters already behind the player.
    percent: Math.round(((chapter - 1) / total) * 100),
    final: Boolean(progress.final),
  };
}
