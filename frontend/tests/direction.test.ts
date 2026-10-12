import { describe, expect, it } from 'vitest'

import { detectDirection, hasRtl, resolveDirection } from '../src/direction'

describe('detectDirection', () => {
  it('detects Arabic as rtl', () => {
    expect(detectDirection('مرحبا بكم في الدارجة')).toBe('rtl')
  })

  it('detects Latin as ltr', () => {
    expect(detectDirection('hello world')).toBe('ltr')
  })

  it('uses the first strong character', () => {
    expect(detectDirection('123 hello')).toBe('ltr')
    expect(detectDirection('123 مرحبا')).toBe('rtl')
    expect(detectDirection('«مرحبا»')).toBe('rtl')
  })

  it('defaults neutral text to ltr', () => {
    expect(detectDirection('')).toBe('ltr')
    expect(detectDirection('123 456 !!!')).toBe('ltr')
  })
})

describe('hasRtl', () => {
  it('finds rtl inside mixed text', () => {
    expect(hasRtl('hello مرحبا')).toBe(true)
    expect(hasRtl('hello')).toBe(false)
  })
})

describe('resolveDirection', () => {
  it('honours an explicit override', () => {
    expect(resolveDirection('ltr', 'مرحبا')).toBe('ltr')
    expect(resolveDirection('rtl', 'hello')).toBe('rtl')
  })

  it('auto-detects when set to auto or null', () => {
    expect(resolveDirection('auto', 'مرحبا')).toBe('rtl')
    expect(resolveDirection(null, 'hello')).toBe('ltr')
  })
})
