import { BAND_SCALE, getBandColor, getBandScaleLabel } from '../colors';

describe('getBandColor', () => {
  it('maps the low band range to red', () => {
    [0, 2.5, 4, 4.5].forEach(band => {
      expect(getBandColor(band)).toBe(BAND_SCALE.low);
    });
  });

  it('maps the mid band range to amber', () => {
    [5, 5.5, 6].forEach(band => {
      expect(getBandColor(band)).toBe(BAND_SCALE.mid);
    });
  });

  it('maps the high band range to lime', () => {
    [6.5, 7].forEach(band => {
      expect(getBandColor(band)).toBe(BAND_SCALE.high);
    });
  });

  it('maps the top band range to green', () => {
    [7.5, 8, 9].forEach(band => {
      expect(getBandColor(band)).toBe(BAND_SCALE.top);
    });
  });

  it('switches colour exactly at the documented boundaries', () => {
    // 4.5 is the last "low" band; 5.0 is the first "mid" band.
    expect(getBandColor(4.5)).toBe(BAND_SCALE.low);
    expect(getBandColor(5)).toBe(BAND_SCALE.mid);
    // 6.0 is the last "mid"; 6.5 is the first "high".
    expect(getBandColor(6)).toBe(BAND_SCALE.mid);
    expect(getBandColor(6.5)).toBe(BAND_SCALE.high);
    // 7.0 is the last "high"; 7.5 is the first "top".
    expect(getBandColor(7)).toBe(BAND_SCALE.high);
    expect(getBandColor(7.5)).toBe(BAND_SCALE.top);
  });
});

describe('getBandScaleLabel', () => {
  it('labels each range', () => {
    expect(getBandScaleLabel(4)).toBe('RED');
    expect(getBandScaleLabel(5.5)).toBe('AMBER');
    expect(getBandScaleLabel(7)).toBe('LIME');
    expect(getBandScaleLabel(8.5)).toBe('GREEN');
  });

  it('agrees with getBandColor across the whole 0-9 scale', () => {
    const labelToColor: Record<string, string> = {
      RED: BAND_SCALE.low,
      AMBER: BAND_SCALE.mid,
      LIME: BAND_SCALE.high,
      GREEN: BAND_SCALE.top,
    };
    for (let band = 0; band <= 9; band += 0.5) {
      expect(labelToColor[getBandScaleLabel(band)]).toBe(getBandColor(band));
    }
  });
});
