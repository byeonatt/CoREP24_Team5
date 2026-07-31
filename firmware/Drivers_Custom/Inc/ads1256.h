#ifndef ADS1256_H
#define ADS1256_H

#include <cstdint>

class ADS1256
{
public:
    void selectChannel(uint8_t channel);
    int32_t readRaw();
};

#endif

enum class Command : uint8_t
{
    WAKEUP = 0x00,
    RDATA  = 0x01,
    RDATAC = 0x03,
    SDATAC = 0x0F,

    RREG   = 0x10,
    WREG   = 0x50,

    SELFCAL = 0xF0,
    SYOCAL  = 0xF1,

    SYGCAL  = 0xF2,
    SYSOCAL = 0xF3,

    RESET = 0xFE
};

enum class Register : uint8_t
{
    STATUS = 0,
    MUX    = 1,
    ADCON  = 2,
    DRATE  = 3,
    IO     = 4
};

class ADS1256
{
public:

    bool initialize();

    bool reset();

    bool selfCalibrate();

    void selectChannel(uint8_t channel);

    int32_t readRaw();

private:

    void writeRegister(...);

    uint8_t readRegister(...);

    void sendCommand(...);
};