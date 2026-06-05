import { useEffect, useState } from 'react';
import { Image, StyleSheet, Text, View } from 'react-native';
import { colors, fonts } from '../theme';
import { fetchMatchQr, type MatchQrWire } from '../lib/runtimeApi';

// A corner badge the TV shows so patrons can scan to put their name on the
// board (ADR 0005). The QR PNG is rendered server-side by the venue box, so
// the TV needs no native QR dependency — it just displays the image. Hidden
// once the match ends (the parent stops rendering it), or if the box can't
// produce a QR (e.g. the qrcode lib isn't installed) we fall back to the
// short play URL as text.

export function JoinQrBadge({ matchId }: { matchId: string }) {
  const [qr, setQr] = useState<MatchQrWire | null>(null);

  useEffect(() => {
    let alive = true;
    // The QR is stable for the life of the match, so fetch once.
    fetchMatchQr(matchId).then((res) => {
      if (alive) setQr(res);
    });
    return () => {
      alive = false;
    };
  }, [matchId]);

  if (!qr) return null;

  return (
    <View style={styles.root}>
      <Text style={styles.caption}>Scan to join</Text>
      {qr.qr_code ? (
        <Image
          style={styles.qr}
          source={{ uri: qr.qr_code }}
          accessibilityLabel="QR code to join the game"
        />
      ) : (
        <Text style={styles.url}>{qr.play_url}</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    position: 'absolute',
    right: 28,
    bottom: 28,
    alignItems: 'center',
    backgroundColor: 'rgba(19, 26, 44, 0.92)',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(248,250,252,0.12)',
    padding: 14,
  },
  caption: {
    fontFamily: fonts.body,
    fontWeight: '700',
    fontSize: 16,
    color: colors.text,
    marginBottom: 8,
  },
  qr: {
    width: 132,
    height: 132,
    borderRadius: 8,
    backgroundColor: '#fff',
  },
  url: {
    fontFamily: fonts.mono,
    fontSize: 13,
    color: colors.textDim,
    maxWidth: 160,
    textAlign: 'center',
  },
});
