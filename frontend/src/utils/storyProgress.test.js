import { test } from 'node:test';
import assert from 'node:assert/strict';
import { describeProgress } from './storyProgress.js';

test('describes the chapter, act and how far along the story is', () => {
  const progress = describeProgress({ chapter: 3, total: 8, act_id: 2, act_title: 'Rising Stakes', final: false });
  assert.deepEqual(progress, {
    chapter: 3, total: 8, label: 'Chapter 3 of 8', act: 'Act 2 · Rising Stakes', percent: 25, final: false,
  });
});

test('the first chapter starts at zero and the final one is flagged', () => {
  assert.equal(describeProgress({ chapter: 1, total: 5, act_id: 1 }).percent, 0);
  const last = describeProgress({ chapter: 5, total: 5, act_id: 2, final: true });
  assert.equal(last.percent, 80);
  assert.equal(last.final, true);
  assert.equal(last.act, 'Act 2');
});

test('no outline means no progress, and odd values are clamped', () => {
  assert.equal(describeProgress(null), null);
  assert.equal(describeProgress({ chapter: 2, total: 0 }), null);
  assert.equal(describeProgress({ chapter: 99, total: 8 }).chapter, 8);
  assert.equal(describeProgress({ chapter: 0, total: 8 }).chapter, 1);
});
