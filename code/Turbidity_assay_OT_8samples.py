### Turbidity Assay

from opentrons import protocol_api

# metadata
metadata = {
    "protocolName": "LP_turbidity_assay_8_samples_in_dilutions",
    "author": "Josefin Sander, Lisa Prigolovkin",
    "description": "Protocol for mixing lysostaphin standard and screening 8 samples in two-fold dilution series for turbidity assay in Opentrons OT-2.",
    "apiLevel": "2.8",
}


# protocol run function
def run(protocol: protocol_api.ProtocolContext):

    ########################### Definitions ############################

    # Modules

    temp_mod = protocol.load_module("temperature module gen2", "10")

    # Labware

    rack = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", "8"
    )  # Eppi rack for standard dilution
    reservoir = protocol.load_labware(
        "ibg_12well_reservoir", "5"
    )  # 12 column reservoir for sensor strain and PBS
    tiprack_1 = protocol.load_labware(
        "opentrons_96_tiprack_300ul", "6"
    )  # 300 uL tiprack
    tiprack_2 = protocol.load_labware(
        "opentrons_96_tiprack_300ul", "9"
    )  # another 300 uL tiprack
    tiprack_3 = protocol.load_labware("vwr_96_tiprack_1000ul", "3")  # 1000 uL tiprack
    assay_plate = protocol.load_labware(
        "greiner_96_wellplate_382ul", "2"
    )  # 96 well plate for turbidity assay
    sample_plate = temp_mod.load_labware(
        "greiner_96_wellplate_382ul"
    )  # 96 well plate containing the samples (cooled)

    # Load pipettes

    p300multi = protocol.load_instrument(
        "p300_multi_gen2", mount="left", tip_racks=[tiprack_1, tiprack_2]
    )
    p1000single = protocol.load_instrument(
        "p1000_single_gen2", mount="right", tip_racks=[tiprack_3]
    )

    # Define variables

    column_list = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
    row_list = ["A", "B", "C", "D", "E", "F", "G", "H"]

    # Reservoir

    sensor_strain_wells = ["A1"]

    PBS_wells = ["A3"]

    # Define wells for standard dilution

    standard_dilution_wells = ["A1", "B1", "C1", "D1", "A2", "B2", "C2", "D2"]

    # Define destination wells for standard on assay MTP

    standard_columns_MTP = ["1", "2", "3"]
    n_replicates = 3
    standard_vol = 100

    sensor_strain_vol = 100

    # TODO: Define columns in sn-MTP which are occupied by samples.

    sample_columns_snMTP = ["1"]

    # Define destination columns on assay MTP

    sample_columns_MTP = ["4", "5", "6", "7", "8", "9", "10", "11", "12"]

    temp_mod.set_temperature(10)

    ########################### Protocol steps ############################

    ########################### Preparation ############################

    # Dilution series of standard

    p1000single.flow_rate.dispense = 500
    p1000single.well_bottom_clearance.aspirate = 10
    p1000single.well_bottom_clearance.dispense = 18

    ## Transfer PBS as diluent to Eppis

    p1000single.transfer(
        500,
        [reservoir.wells_by_name()[well_name] for well_name in PBS_wells],
        [rack.wells_by_name()[well_name] for well_name in standard_dilution_wells[1:]],
    )

    ## Dilution series until second to last Eppi (last Eppi = negative control)

    p1000single.pick_up_tip()
    p1000single.mix(8, 500, rack.wells_by_name()["A1"])
    p1000single.drop_tip()

    for i in range(len(standard_dilution_wells) - 2):
        p1000single.pick_up_tip()
        p1000single.transfer(
            500,
            rack.wells()[i],
            rack.wells()[i + 1],
            mix_after=(8, 500),
            new_tip="never",
        )
        p1000single.drop_tip()

    p1000single.well_bottom_clearance.aspirate = 3
    p1000single.well_bottom_clearance.dispense = 2

    ########################### Assay MTP ############################

    # Transfer standard dilution series to assay MTP

    for i in range(len(row_list)):
        p1000single.pick_up_tip()
        p1000single.aspirate(n_replicates * standard_vol, rack.wells()[i])
        for j in range(n_replicates):
            p1000single.dispense(
                standard_vol,
                assay_plate.wells_by_name()[f"{row_list[i]}{standard_columns_MTP[j]}"],
            )
        p1000single.drop_tip()

    # Dilution series of samples

    ## Transfer PBS to assay MTP for sample dilution series

    p300multi.distribute(
        100,
        [reservoir.wells_by_name()[well_name] for well_name in PBS_wells],
        [
            assay_plate.columns_by_name()[column_name]
            for column_name in sample_columns_MTP[1:]
        ],
        blow_out=True,
        blowout_location="source well",
    )

    ## Mix and transfer samples from sn-MTP to assay MTP

    p300multi.flow_rate.dispense = 150

    p300multi.transfer(
        200,
        sample_plate.columns_by_name()[sample_columns_snMTP[0]],
        assay_plate.columns_by_name()[sample_columns_MTP[0]],
        mix_before=(5, 200),
        new_tip="always",
        blow_out=True,
        blowout_location="destination well",
    )

    # Dilution of samples in assay MTP, using new tips for every step

    p300multi.well_bottom_clearance.aspirate = 2
    p300multi.well_bottom_clearance.dispense = 2

    p300multi.transfer(
        100,
        [
            assay_plate.columns_by_name()[column_name]
            for column_name in sample_columns_MTP[:-1]
        ],
        [
            assay_plate.columns_by_name()[column_name]
            for column_name in sample_columns_MTP[1:]
        ],
        mix_after=(8, 100),
        new_tip="always",
        blow_out=True,
        blowout_location="destination well",
    )

    p300multi.transfer(
        100,
        assay_plate.columns_by_name()[sample_columns_MTP[-1]],
        protocol.fixed_trash["A1"],
    )

    # Addition of sensor strain to start assay

    protocol.pause(
        "Photometer ready? User ready? Proceed to start assay by adding the sensor strain."
    )

    p300multi.flow_rate.dispense = 250

    # Optional mixing step if sensor strain is provided before script is started
    # p300multi.pick_up_tip()
    # p300multi.mix(8,200, reservoir.wells_by_name()[f'{sensor_strain_wells[0]}'])
    # p300multi.drop_tip()

    target_columns = column_list[::-1]

    p300multi.well_bottom_clearance.dispense = 12

    p300multi.pick_up_tip()

    for i in range(len(target_columns)):
        p300multi.aspirate(100, reservoir.wells_by_name()[f"{sensor_strain_wells[0]}"])
        p300multi.dispense(
            100, assay_plate.wells_by_name()[f"{row_list[0]}{target_columns[i]}"]
        )
        p300multi.blow_out()
        p300multi.touch_tip()

    p300multi.drop_tip()

    protocol.pause("Place assay MTP in Photometer.")
